import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchRequest, editRequest, fetchEvents } from '../api/requests';
import { Request, EditRequestInput, RequestEvent, PaginatedResponse } from '../types';
import { parseApiError } from '../api/client';

export const useRequest = (id: string | number) => {
  const queryClient = useQueryClient();

  const query = useQuery<Request, Error>({
    queryKey: ['request', String(id)],
    queryFn: () => fetchRequest(id),
    enabled: !!id,
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
  });

  const eventsQuery = useQuery<PaginatedResponse<RequestEvent> | RequestEvent[], Error>({
    queryKey: ['events', String(id)],
    queryFn: () => fetchEvents(id),
    enabled: !!id,
    refetchInterval: 15000,
  });

  const events: RequestEvent[] = Array.isArray(eventsQuery.data)
    ? eventsQuery.data
    : eventsQuery.data?.items ?? [];

  const editMutation = useMutation({
    mutationFn: ({ data, version }: { data: EditRequestInput; version: number }) =>
      editRequest(id, data, version),
    onMutate: async ({ data }) => {
      await queryClient.cancelQueries({ queryKey: ['request', String(id)] });
      const previousRequest = queryClient.getQueryData<Request>(['request', String(id)]);

      if (previousRequest) {
        queryClient.setQueryData<Request>(['request', String(id)], {
          ...previousRequest,
          ...data,
          version: previousRequest.version + 1,
          updated_at: new Date().toISOString(),
        });
      }

      return { previousRequest };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousRequest) {
        queryClient.setQueryData(['request', String(id)], context.previousRequest);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['request', String(id)] });
      queryClient.invalidateQueries({ queryKey: ['requests'] });
      queryClient.invalidateQueries({ queryKey: ['events', String(id)] });
    },
  });

  return {
    ...query,
    request: query.data,
    events,
    isLoadingEvents: eventsQuery.isLoading,
    currentVersion: query.data?.version,
    editMutation,
    editError: editMutation.error ? parseApiError(editMutation.error) : null,
  };
};

export default useRequest;
