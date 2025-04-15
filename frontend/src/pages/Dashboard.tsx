import React, { useEffect, useState } from 'react';
import { Container, Grid, Stack, Text, LoadingOverlay } from '@mantine/core';
import { ListingCard } from '../components/ListingCard';
import { SearchBar } from '../components/SearchBar';
import { FilterPanel } from '../components/FilterPanel';
import { useListings } from '../hooks/useListings';
import { Listing } from '../types';

export const Dashboard: React.FC = () => {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<string | null>(null);
  const { listings, isLoading, error } = useListings({ category });
  
  const filteredListings = listings.filter(listing => 
    listing.title.toLowerCase().includes(search.toLowerCase()) ||
    listing.description.toLowerCase().includes(search.toLowerCase())
  );

  if (error) {
    return (
      <Container>
        <Text color="red">Error loading listings: {error.message}</Text>
      </Container>
    );
  }

  return (
    <Container size="xl" py="xl">
      <Stack spacing="md">
        <SearchBar
          value={search}
          onChange={setSearch}
          onClear={() => setSearch('')}
        />
        
        <Grid>
          <Grid.Col span={3}>
            <FilterPanel
              selectedCategory={category}
              onCategoryChange={setCategory}
            />
          </Grid.Col>
          
          <Grid.Col span={9}>
            <Grid>
              {filteredListings.map((listing) => (
                <Grid.Col key={listing.id} span={4}>
                  <ListingCard
                    title={listing.title}
                    price={listing.price}
                    location={listing.location}
                    description={listing.description}
                    imageUrl={listing.images[0]?.url}
                    category={listing.category}
                    confidence={listing.analysis.confidence}
                    onViewDetails={() => {/* Implement navigation */}}
                  />
                </Grid.Col>
              ))}
            </Grid>
          </Grid.Col>
        </Grid>
      </Stack>
      
      <LoadingOverlay visible={isLoading} />
    </Container>
  );
};
