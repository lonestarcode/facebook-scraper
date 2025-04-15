'use client';

import React from 'react';
import { Container, Grid, Card, Text, Group, Badge, Button, Image, Carousel, Stack, LoadingOverlay, Alert, SimpleGrid, Progress } from '@mantine/core';
import { IconAlertCircle, IconChevronLeft, IconExternalLink, IconMapPin, IconCalendar, IconTag } from '@tabler/icons-react';
import { useListing } from '@/hooks/useListings';
import { useRouter } from 'next/navigation';

interface ListingDetailProps {
  id: string;
}

export const ListingDetail: React.FC<ListingDetailProps> = ({ id }) => {
  const router = useRouter();
  const { listing, isLoading, error } = useListing(id);

  if (error) {
    return (
      <Container size="md" py="xl">
        <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red">
          {error.message || 'Failed to load listing details'}
        </Alert>
        <Button 
          leftIcon={<IconChevronLeft size={16} />} 
          mt="md" 
          variant="subtle" 
          onClick={() => router.push('/dashboard')}
        >
          Back to listings
        </Button>
      </Container>
    );
  }

  return (
    <Container size="lg" py="xl">
      <LoadingOverlay visible={isLoading} />
      
      {listing && (
        <Stack spacing="xl">
          <Group position="apart">
            <Button 
              leftIcon={<IconChevronLeft size={16} />} 
              variant="subtle" 
              onClick={() => router.push('/dashboard')}
            >
              Back to listings
            </Button>
            
            <Button 
              variant="light" 
              color="blue" 
              component="a" 
              href={listing.listing_url} 
              target="_blank" 
              rel="noopener noreferrer"
              rightIcon={<IconExternalLink size={16} />}
            >
              View on Facebook
            </Button>
          </Group>
          
          <Grid>
            <Grid.Col md={7}>
              {listing.images && listing.images.length > 0 ? (
                <Card radius="md" padding="xs">
                  <Carousel
                    withIndicators
                    height={400}
                    slideSize="100%"
                    slideGap="md"
                    loop
                  >
                    {listing.images.map((image, index) => (
                      <Carousel.Slide key={index}>
                        <Image
                          src={image.url}
                          height={400}
                          fit="contain"
                          alt={image.alt || `${listing.title} - Image ${index + 1}`}
                          withPlaceholder
                        />
                      </Carousel.Slide>
                    ))}
                  </Carousel>
                </Card>
              ) : (
                <Image
                  src="/placeholder.png"
                  height={400}
                  alt={listing.title}
                />
              )}
            </Grid.Col>
            
            <Grid.Col md={5}>
              <Card shadow="sm" padding="lg" radius="md" withBorder>
                <Stack spacing="md">
                  <Text size="xl" weight={700}>{listing.title}</Text>
                  
                  <Group position="apart">
                    <Badge size="xl" color="green" variant="light">
                      ${listing.price}
                    </Badge>
                    <Group spacing="xs">
                      <IconMapPin size={16} />
                      <Text size="sm">{listing.location}</Text>
                    </Group>
                  </Group>
                  
                  <Group spacing="xs">
                    <IconCalendar size={16} />
                    <Text size="sm">
                      Posted: {new Date(listing.created_at).toLocaleDateString()}
                    </Text>
                  </Group>
                  
                  <Group spacing="xs">
                    <IconTag size={16} />
                    <Text size="sm">Category: {listing.category}</Text>
                  </Group>
                  
                  {listing.analysis && (
                    <>
                      <Text weight={600} mt="md">Listing Analysis</Text>
                      
                      <Stack spacing="xs">
                        <Text size="sm">Quality Score:</Text>
                        <Progress 
                          value={listing.analysis.quality_score * 100} 
                          color={listing.analysis.quality_score > 0.7 ? "green" : listing.analysis.quality_score > 0.4 ? "yellow" : "red"}
                          size="xl"
                          radius="xl"
                          striped
                          animate
                        />
                        
                        <Text size="sm" mt="xs">Category Confidence:</Text>
                        <Progress 
                          value={listing.analysis.category_confidence * 100} 
                          color="blue"
                          size="xl"
                          radius="xl"
                        />
                      </Stack>
                      
                      {listing.analysis.keywords && listing.analysis.keywords.length > 0 && (
                        <>
                          <Text weight={500} size="sm">Keywords:</Text>
                          <Group spacing="xs">
                            {listing.analysis.keywords.map((keyword, index) => (
                              <Badge key={index} variant="outline">
                                {keyword}
                              </Badge>
                            ))}
                          </Group>
                        </>
                      )}
                    </>
                  )}
                  
                  <Button fullWidth mt="md" color="blue">
                    Create Price Alert
                  </Button>
                </Stack>
              </Card>
            </Grid.Col>
          </Grid>
          
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Text weight={600} mb="md">Description</Text>
            <Text>
              {listing.description || 'No description provided.'}
            </Text>
          </Card>
        </Stack>
      )}
    </Container>
  );
}; 