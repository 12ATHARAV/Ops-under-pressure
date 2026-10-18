import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { transitionRequest } from '../api/requests';
import { generateIdempotencyKey, parseApiError } from '../api/client';
import { Request, RequestStatus, ApiError } from '../types';

export interface TransitionVariables {
  requestId: string | number;
  to: RequestStatus | string;
  version: number;
  reason?: string;
}

export const useTransition = () => {
  const queryClient = useQueryClient();
  const [conflict, setConflict] = useState<{
    isOpen: boolean;
    error: ApiError | null;
    requestId: string | number | null;
  }>({
    isOpen: false,
    error: null,
    requestId: null,
  });

  const mutation = useMutation({
    mutationFn: async ({ requestId, to, version, reason }: TransitionVariables) => {
      const idempotencyKey = generateIdempotencyKey();
      return transitionRequest(requestId, to, version, reason, idempotencyKey);
    },
    onMutate: async ({ requestId, to }) => {
      await queryClient.cancelQueries({ queryKey: ['request', String(requestId)] });
      const previousRequest = queryClient.getQueryData<Request>(['request', String(requestId)]);

      if (previousRequest) {
        queryClient.setQueryData<Request>(['request', String(requestId)], {
          ...previousRequest,
          status: to as RequestStatus,
          version: previousRequest.version + 1,
          last_activity_at: new Date().toISOString(),
        });
      }

      return { previousRequest, requestId };
    },
    onError: (err: any, variables, context) => {
      if (context?.previousRequest && context?.requestId) {
        queryClient.setQueryData(
          ['request', String(context.requestId)],
          context.previousRequest
        );
      }

      const parsedError = parseApiError(err);
      if (err?.response?.status === 409) {
        setConflict({
          isOpen: true,
          error: parsedError,
          requestId: variables.requestId,
        });
      }
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: ['request', String(variables.requestId)] });
      queryClient.invalidateQueries({ queryKey: ['requests'] });
      queryClient.invalidateQueries({ queryKey: ['events', String(variables.requestId)] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['attention'] });
    },
  });

  const closeConflictDialog = () => {
    setConflict({
      isOpen: false,
      error: null,
      requestId: null,
    });
  };

  return {
    ...mutation,
    conflict,
    closeConflictDialog,
  };
};

export default useTransition;
