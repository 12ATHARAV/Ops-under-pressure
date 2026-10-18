import { useInfiniteQuery } from '@tanstack/react-query';
import { fetchRequests } from '../api/requests';
import { RequestFilters, PaginatedResponse, Request } from '../types';

export const useRequests = (filters: RequestFilters = {}) => {
  const query = useInfiniteQuery<PaginatedResponse<Request>, Error>({
    queryKey: ['requests', filters],
    queryFn: ({ pageParam }) => fetchRequests(filters, (pageParam as string | null) ?? null),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => (lastPage.has_more ? lastPage.cursor : undefined),
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
  });

  const requests: Request[] = query.data?.pages.flatMap((page) => page.items) ?? [];

  return {
    ...query,
    requests,
  };
};

export default useRequests;
