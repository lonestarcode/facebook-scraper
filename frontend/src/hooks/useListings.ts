'use client';

import useSWR from 'swr';
import { listingsApi } from '@/lib/api';
import { FilterOptions, Listing } from '@/types';

const fetcher = (url: string, options?: FilterOptions) => 
  listingsApi.getListings(options).then(data => data);

export function useListings(options?: FilterOptions) {
  const { data, error, isLoading, mutate } = useSWR(
    ['listings', options],
    () => fetcher('/listings', options),
    {
      refreshInterval: 30000, // Refresh every 30 seconds
      revalidateOnFocus: true,
    }
  );

  return {
    listings: data?.listings || [],
    total: data?.total || 0,
    isLoading,
    error,
    mutate,
  };
}

export function useListing(id: string) {
  const { data, error, isLoading } = useSWR(
    id ? `listing-${id}` : null,
    () => listingsApi.getListing(id),
    {
      revalidateOnFocus: false,
    }
  );

  return {
    listing: data,
    isLoading,
    error,
  };
} 