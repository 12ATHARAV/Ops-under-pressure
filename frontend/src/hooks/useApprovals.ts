import { useQuery } from '@tanstack/react-query';
import { fetchApprovalQueue } from '../api/requests';
import { PaginatedResponse, Request } from '../types';

export const useApprovals = (cursor: string | null = null, enabled: boolean = true) => {
  const query = useQuery<PaginatedResponse<Request>, Error>({
    queryKey: ['approvals', cursor],
    queryFn: () => fetchApprovalQueue(cursor),
    enabled,
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
  });

  const requests: Request[] = query.data?.items ?? [];

  return {
    ...query,
    requests,
  };
};

export default useApprovals;
