import { useQuery } from '@tanstack/react-query';
import { fetchAttention } from '../api/requests';
import { AttentionResponse, AttentionBucket } from '../types';

export const useAttention = (enabled: boolean = true) => {
  const query = useQuery<AttentionResponse, Error>({
    queryKey: ['attention'],
    queryFn: () => fetchAttention(),
    enabled,
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
  });

  const buckets: AttentionBucket[] = query.data?.buckets ?? [];

  return {
    ...query,
    buckets,
  };
};

export default useAttention;
