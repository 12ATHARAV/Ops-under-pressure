import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { claimRequest } from '../api/requests';
import { generateIdempotencyKey, parseApiError } from '../api/client';
import { Request, User, ApiError } from '../types';

export const useClaim = () => {
  const queryClient = useQueryClient();
  const [claimError, setClaimError] = useState<ApiError | null>(null);

  const mutation = useMutation({
    mutationFn: async ({
      requestId,
      user: _user,
    }: {
      requestId: string | number;
      user: User;
    }) => {
      setClaimError(null);
      const idempotencyKey = generateIdempotencyKey();
      return claimRequest(requestId, idempotencyKey);
    },
    onMutate: async ({ requestId, user }) => {
      await queryClient.cancelQueries({ queryKey: ['request', String(requestId)] });
      const previousRequest = queryClient.getQueryData<Request>(['request', String(requestId)]);

      if (previousRequest) {
        queryClient.setQueryData<Request>(['request', String(requestId)], {
          ...previousRequest,
          owner_id: user.id,
          owner_name: user.name,
          version: previousRequest.version + 1,
          last_activity_at: new Date().toISOString(),
          allowed_actions: previousRequest.allowed_actions.filter((a) => a !== 'claim'),
        });
      }

      return { previousRequest, requestId };
    },
    onError: (err, _variables, context) => {
      if (context?.previousRequest && context?.requestId) {
        queryClient.setQueryData(
          ['request', String(context.requestId)],
          context.previousRequest
        );
      }
      const parsed = parseApiError(err);
      setClaimError(parsed);
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: ['request', String(variables.requestId)] });
      queryClient.invalidateQueries({ queryKey: ['requests'] });
      queryClient.invalidateQueries({ queryKey: ['events', String(variables.requestId)] });
    },
  });

  return {
    ...mutation,
    claimError,
    clearError: () => setClaimError(null),
  };
};

export default useClaim;
