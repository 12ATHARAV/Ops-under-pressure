import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchNotifications, markRead } from '../api/notifications';
import { Notification, PaginatedResponse } from '../types';

export const useNotifications = () => {
  const queryClient = useQueryClient();

  const query = useQuery<PaginatedResponse<Notification>, Error>({
    queryKey: ['notifications'],
    queryFn: () => fetchNotifications(),
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
  });

  const notifications: Notification[] = query.data?.items ?? [];
  const unreadCount = notifications.filter((n) => !n.read_at).length;

  const markReadMutation = useMutation({
    mutationFn: (id: string | number) => markRead(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['notifications'] });
      const previousData = queryClient.getQueryData<PaginatedResponse<Notification>>(['notifications']);

      if (previousData) {
        queryClient.setQueryData<PaginatedResponse<Notification>>(['notifications'], {
          ...previousData,
          items: previousData.items.map((n) =>
            n.id === id ? { ...n, read_at: new Date().toISOString() } : n
          ),
        });
      }

      return { previousData };
    },
    onError: (_err, _id, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(['notifications'], context.previousData);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  return {
    ...query,
    notifications,
    unreadCount,
    markAsRead: markReadMutation.mutate,
    isMarkingRead: markReadMutation.isPending,
  };
};

export default useNotifications;
