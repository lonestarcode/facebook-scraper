'use client';

import React, { useState } from 'react';
import { Card, Stack, Title, Select, NumberInput, Button, TextInput, MultiSelect } from '@mantine/core';

interface FilterPanelProps {
  selectedCategory: string | null;
  onCategoryChange: (category: string | null) => void;
  onFilterChange?: (filters: any) => void;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  selectedCategory,
  onCategoryChange,
  onFilterChange,
}) => {
  const [minPrice, setMinPrice] = useState<number | undefined>(undefined);
  const [maxPrice, setMaxPrice] = useState<number | undefined>(undefined);
  const [location, setLocation] = useState<string>('');
  const [keywords, setKeywords] = useState<string[]>([]);

  const categories = [
    { value: 'bikes', label: 'Bikes' },
    { value: 'electronics', label: 'Electronics' },
    { value: 'furniture', label: 'Furniture' },
    { value: 'clothing', label: 'Clothing' },
    { value: 'cars', label: 'Cars' },
  ];

  const handleApplyFilters = () => {
    if (onFilterChange) {
      onFilterChange({
        category: selectedCategory,
        minPrice,
        maxPrice,
        location: location.trim() || undefined,
        keywords: keywords.length > 0 ? keywords : undefined,
      });
    }
  };

  const handleClearFilters = () => {
    onCategoryChange(null);
    setMinPrice(undefined);
    setMaxPrice(undefined);
    setLocation('');
    setKeywords([]);
    
    if (onFilterChange) {
      onFilterChange({});
    }
  };

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Stack spacing="md">
        <Title order={3}>Filters</Title>
        
        <Select
          label="Category"
          placeholder="Select a category"
          data={categories}
          value={selectedCategory}
          onChange={onCategoryChange}
          clearable
        />
        
        <NumberInput
          label="Min Price"
          placeholder="Enter min price"
          value={minPrice}
          onChange={(val) => setMinPrice(val || undefined)}
          min={0}
        />
        
        <NumberInput
          label="Max Price"
          placeholder="Enter max price"
          value={maxPrice}
          onChange={(val) => setMaxPrice(val || undefined)}
          min={0}
        />
        
        <TextInput
          label="Location"
          placeholder="Enter location"
          value={location}
          onChange={(e) => setLocation(e.currentTarget.value)}
        />
        
        <MultiSelect
          label="Keywords"
          placeholder="Enter keywords"
          data={keywords.map(k => ({ value: k, label: k }))}
          value={keywords}
          onChange={setKeywords}
          searchable
          creatable
          getCreateLabel={(query) => `+ Add ${query}`}
          onCreate={(query) => {
            setKeywords((current) => [...current, query]);
            return query;
          }}
        />
        
        <Button.Group>
          <Button fullWidth onClick={handleApplyFilters}>
            Apply Filters
          </Button>
          <Button fullWidth variant="light" onClick={handleClearFilters}>
            Clear Filters
          </Button>
        </Button.Group>
      </Stack>
    </Card>
  );
};
