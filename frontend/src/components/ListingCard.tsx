import React from 'react';
import { Card, Image, Text, Badge, Group, Button } from '@mantine/core';

interface ListingCardProps {
  title: string;
  price: number;
  location: string;
  description: string;
  imageUrl: string;
  category: string;
  confidence: number;
  onViewDetails: () => void;
}

export const ListingCard: React.FC<ListingCardProps> = ({
  title,
  price,
  location,
  description,
  imageUrl,
  category,
  confidence,
  onViewDetails,
}) => {
  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Card.Section>
        <Image
          src={imageUrl}
          height={200}
          alt={title}
          fallbackSrc="/placeholder.png"
        />
      </Card.Section>

      <Group position="apart" mt="md" mb="xs">
        <Text weight={500}>{title}</Text>
        <Badge color="green" variant="light">
          ${price}
        </Badge>
      </Group>

      <Text size="sm" color="dimmed" lineClamp={2}>
        {description}
      </Text>

      <Group position="apart" mt="md">
        <Text size="sm" color="gray">
          {location}
        </Text>
        <Badge color="blue" variant="light">
          {category} ({(confidence * 100).toFixed(1)}%)
        </Badge>
      </Group>

      <Button variant="light" color="blue" fullWidth mt="md" radius="md" onClick={onViewDetails}>
        View Details
      </Button>
    </Card>
  );
};
