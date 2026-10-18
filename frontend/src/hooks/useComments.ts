import { useMutation, useQueryClient } from '@tanstack/react-query';
import { addComment } from '../api/requests';
import { generateIdempotencyKey } from '../api/client';
import { User } from '../types';

export const useComments = (requestId: string | number) => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ body }: { body: string; user?: User }) => {
      const idempotencyKey = generateIdempotencyKey();
      return addComment(requestId, body, idempotencyKey);
    },
    onMutate: async ({ body, user }) => {
      await queryClient.cancelQueries({ queryKey: ['events', String(requestId)] });

      const previousEvents = queryClient.getQueryData<any>(['events', String(requestId)]);

      const optimisticCommentEvent = {
        id: 'temp-' + Date.now(),
        request_id: requestId,
        actor_id: user?.id ?? 0,
        actor_name: user?.name ?? 'You',
        type: 'commented',
        from_value: null,
        to_value: { body },
        reason: null,
        created_at: new Date().toISOString(),
      };

      if (Array.isArray(previousEvents)) {
        queryClient.setQueryData(['events', String(requestId)], [
          ...previousEvents,
          optimisticCommentEvent,
        ]);
      } else if (previousEvents?.items) {
        queryClient.setQueryData(['events', String(requestId)], {
          ...previousEvents,
          items: [...previousEvents.items, optimisticCommentEvent],
        });
      }

      return { previousEvents };
    },
    onError: (_err, _variables, context) => {
      if (context?.previousEvents) {
        queryClient.setQueryData(['events', String(requestId)], context.previousEvents);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['events', String(requestId)] });
      queryClient.invalidateQueries({ queryKey: ['request', String(requestId)] });
    },
  });

  return {
    addCommentMutation: mutation,
  };
};

export default useComments;
