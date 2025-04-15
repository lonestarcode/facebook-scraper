'use client';

import React, { useState, useEffect } from 'react';
import { Container, Grid, Stack, Text, LoadingOverlay, Pagination, Alert, Group, Button } from '@mantine/core';
import { IconAlertCircle, IconWifi, IconWifiOff } from '@tabler/icons-react';
import { useRouter } from 'next/navigation';
import { ListingCard } from './ListingCard';
import { SearchBar } from './SearchBar';
import { FilterPanel } from './FilterPanel';
import { useListings } from '@/hooks/useListings';
import { useListingWebSocket } from '@/lib/websocket';
import { FilterOptions, Listing } from '@/types';

export const DashboardContent: React.FC = () => {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FilterOptions>({});
  const { listings, isLoading, error, total } = useListings(filters);
  const { listings: wsListings, connected: wsConnected } = useListingWebSocket(filters.category || 'all');
  
  const itemsPerPage = 9;
  const totalPages = Math.ceil(total / itemsPerPage);
  
  // Merge listings from API and WebSocket for real-time updates
  const [mergedListings, setMergedListings] = useState<Listing[]>([]);
  
  useEffect(() => {
    if (wsListings.length > 0) {
      // Create a map of existing listings by ID
      const listingMap = new Map(listings.map(l => [l.id, l]));
      
      // Add new listings from WebSocket
      wsListings.forEach(wsListing => {
        if (!listingMap.has(wsListing.id)) {
          listingMap.set(wsListing.id, wsListing);
        }
      });
      
      setMergedListings(Array.from(listingMap.values()));
    } else {
      setMergedListings(listings);
    }
  }, [listings, wsListings]);
  
  const filteredListings = mergedListings.filter(listing => 
    listing.title.toLowerCase().includes(search.toLowerCase()) ||
    listing.description.toLowerCase().includes(search.toLowerCase())
  );
  
  // Calculate paginated listings
  const startIndex = (page - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedListings = filteredListings.slice(startIndex, endIndex);

  const handleViewDetails = (id: number) => {
    router.push(`/listings/${id}`);
  };
  
  const handleFilterChange = (newFilters: FilterOptions) => {
    setFilters(newFilters);
    setPage(1); // Reset to first page when filters change
  };

  return (
    <Container size="xl" py="xl">
      <Stack spacing="md">
        <Group position="apart">
          <Text size="xl" weight={700}>Facebook Marketplace Listings</Text>
          <Group>
            {wsConnected ? (
              <Group spacing="xs">
                <IconWifi size={18} color="green" />
                <Text size="sm" color="green">Live updates connected</Text>
              </Group>
            ) : (
              <Group spacing="xs">
                <IconWifiOff size={18} color="gray" />
                <Text size="sm" color="gray">Offline mode</Text>
              </Group>
            )}
            
            <Button
              variant="outline"
              onClick={() => router.push('/alerts')}
            >
              Manage Alerts
            </Button>
          </Group>
        </Group>
      
        <SearchBar
          value={search}
          onChange={setSearch}
          onClear={() => setSearch('')}
        />
        
        <Grid>
          <Grid.Col span={3}>
            <FilterPanel
              selectedCategory={filters.category || null}
              onCategoryChange={(cat) => handleFilterChange({ ...filters, category: cat || undefined })}
              onFilterChange={handleFilterChange}
            />
          </Grid.Col>
          
          <Grid.Col span={9}>
            {error ? (
              <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red">
                Error loading listings: {error.message}
              </Alert>
            ) : (
              <>
                <Grid>
                  {paginatedListings.length > 0 ? (
                    paginatedListings.map((listing) => (
                      <Grid.Col key={listing.id} span={4}>
                        <ListingCard
                          title={listing.title}
                          price={listing.price}
                          location={listing.location}
                          description={listing.description || ''}
                          imageUrl={listing.images?.[0]?.url || '/placeholder.png'}
                          category={listing.category}
                          confidence={listing.analysis?.confidence || 0}
                          onViewDetails={() => handleViewDetails(listing.id)}
                        />
                      </Grid.Col>
                    ))
                  ) : (
                    <Grid.Col span={12}>
                      <Text align="center" mt="xl">
                        {isLoading ? 'Loading listings...' : 'No listings found matching your criteria.'}
                      </Text>
                    </Grid.Col>
                  )}
                </Grid>
                
                {totalPages > 1 && (
                  <Group position="center" mt="xl">
                    <Pagination
                      total={totalPages}
                      value={page}
                      onChange={setPage}
                      withEdges
                    />
                  </Group>
                )}
              </>
            )}
          </Grid.Col>
        </Grid>
      </Stack>
      
      <LoadingOverlay visible={isLoading} />
    </Container>
  );
}; 