'use client';

import React, { useState } from 'react';
import { Container, Title, Stack, Card, Group, Text, Button, Modal, TextInput, Select, NumberInput, MultiSelect, Switch, Grid, ActionIcon, Badge, Alert } from '@mantine/core';
import { IconAlertCircle, IconBell, IconChevronLeft, IconEdit, IconPlus, IconTrash } from '@tabler/icons-react';
import { useRouter } from 'next/navigation';
import useSWR, { mutate } from 'swr';
import { alertsApi } from '@/lib/api';
import { PriceAlert } from '@/types';

export const AlertsManager: React.FC = () => {
  const router = useRouter();
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [currentAlert, setCurrentAlert] = useState<PriceAlert | null>(null);
  
  // Form state
  const [category, setCategory] = useState<string>('');
  const [maxPrice, setMaxPrice] = useState<number>(0);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [email, setEmail] = useState<string>('');
  const [webhook, setWebhook] = useState<string>('');
  const [isActive, setIsActive] = useState(true);
  
  // Fetch alerts
  const { data: alerts, error } = useSWR('alerts', alertsApi.getAlerts);
  
  const categories = [
    { value: 'bikes', label: 'Bikes' },
    { value: 'electronics', label: 'Electronics' },
    { value: 'furniture', label: 'Furniture' },
    { value: 'clothing', label: 'Clothing' },
    { value: 'cars', label: 'Cars' },
  ];
  
  const resetForm = () => {
    setCategory('');
    setMaxPrice(0);
    setKeywords([]);
    setEmail('');
    setWebhook('');
    setIsActive(true);
  };
  
  const handleCreateAlert = async () => {
    try {
      await alertsApi.createAlert({
        user_id: 'current_user', // This would be a real user ID in a production app
        category,
        max_price: maxPrice,
        keywords,
        notify_email: email,
        notify_webhook: webhook || undefined,
        is_active: isActive,
      });
      
      mutate('alerts');
      setCreateModalOpen(false);
      resetForm();
    } catch (error) {
      console.error('Error creating alert:', error);
    }
  };
  
  const handleEditAlert = async () => {
    if (!currentAlert) return;
    
    try {
      await alertsApi.updateAlert(currentAlert.id, {
        category,
        max_price: maxPrice,
        keywords,
        notify_email: email,
        notify_webhook: webhook || undefined,
        is_active: isActive,
      });
      
      mutate('alerts');
      setEditModalOpen(false);
      setCurrentAlert(null);
      resetForm();
    } catch (error) {
      console.error('Error updating alert:', error);
    }
  };
  
  const handleDeleteAlert = async (id: number) => {
    try {
      await alertsApi.deleteAlert(id);
      mutate('alerts');
    } catch (error) {
      console.error('Error deleting alert:', error);
    }
  };
  
  const openEditModal = (alert: PriceAlert) => {
    setCurrentAlert(alert);
    setCategory(alert.category);
    setMaxPrice(alert.max_price);
    setKeywords(alert.keywords);
    setEmail(alert.notify_email);
    setWebhook(alert.notify_webhook || '');
    setIsActive(alert.is_active);
    setEditModalOpen(true);
  };
  
  return (
    <Container size="lg" py="xl">
      <Stack spacing="xl">
        <Group position="apart">
          <Group spacing="xs">
            <Button 
              leftIcon={<IconChevronLeft size={16} />} 
              variant="subtle" 
              onClick={() => router.push('/dashboard')}
            >
              Back to listings
            </Button>
            <Title order={2}>Price Alerts</Title>
          </Group>
          
          <Button 
            leftIcon={<IconPlus size={16} />} 
            onClick={() => {
              resetForm();
              setCreateModalOpen(true);
            }}
          >
            Create Alert
          </Button>
        </Group>
        
        {error && (
          <Alert icon={<IconAlertCircle size={16} />} title="Error" color="red">
            {error.message || 'Failed to load alerts'}
          </Alert>
        )}
        
        <Grid>
          {alerts?.length ? (
            alerts.map((alert) => (
              <Grid.Col key={alert.id} md={6} lg={4}>
                <Card shadow="sm" padding="lg" radius="md" withBorder>
                  <Card.Section px="lg" py="md" bg="blue.1">
                    <Group position="apart">
                      <Group spacing="xs">
                        <IconBell size={20} color={alert.is_active ? 'blue' : 'gray'} />
                        <Text weight={500}>{categories.find(c => c.value === alert.category)?.label || alert.category}</Text>
                      </Group>
                      <Badge color={alert.is_active ? 'green' : 'gray'}>
                        {alert.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </Group>
                  </Card.Section>
                  
                  <Stack spacing="xs" mt="md">
                    <Group position="apart">
                      <Text size="sm" color="dimmed">Max Price:</Text>
                      <Text weight={500}>${alert.max_price}</Text>
                    </Group>
                    
                    <Group position="apart">
                      <Text size="sm" color="dimmed">Notification:</Text>
                      <Text size="sm" style={{ wordBreak: 'break-all' }}>{alert.notify_email}</Text>
                    </Group>
                    
                    {alert.keywords.length > 0 && (
                      <Stack spacing="xs">
                        <Text size="sm" color="dimmed">Keywords:</Text>
                        <Group spacing="xs">
                          {alert.keywords.map((keyword, idx) => (
                            <Badge key={idx} size="sm" variant="outline">{keyword}</Badge>
                          ))}
                        </Group>
                      </Stack>
                    )}
                  </Stack>
                  
                  <Group position="right" mt="lg">
                    <ActionIcon color="blue" onClick={() => openEditModal(alert)}>
                      <IconEdit size={16} />
                    </ActionIcon>
                    <ActionIcon color="red" onClick={() => handleDeleteAlert(alert.id)}>
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Group>
                </Card>
              </Grid.Col>
            ))
          ) : (
            <Grid.Col span={12}>
              <Text align="center" color="dimmed" py="xl">
                {error ? 'Error loading alerts' : !alerts ? 'Loading alerts...' : 'No alerts created yet'}
              </Text>
            </Grid.Col>
          )}
        </Grid>
      </Stack>
      
      {/* Create Alert Modal */}
      <Modal
        opened={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create Price Alert"
        size="lg"
      >
        <Stack spacing="md">
          <Select
            label="Category"
            placeholder="Select a category"
            data={categories}
            value={category}
            onChange={(val) => setCategory(val || '')}
            required
          />
          
          <NumberInput
            label="Maximum Price"
            placeholder="Enter maximum price"
            value={maxPrice}
            onChange={(val) => setMaxPrice(val || 0)}
            min={0}
            required
          />
          
          <MultiSelect
            label="Keywords"
            placeholder="Enter keywords to match"
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
          
          <TextInput
            label="Email"
            placeholder="Enter notification email"
            value={email}
            onChange={(e) => setEmail(e.currentTarget.value)}
            required
          />
          
          <TextInput
            label="Webhook URL (Optional)"
            placeholder="Enter webhook URL for notifications"
            value={webhook}
            onChange={(e) => setWebhook(e.currentTarget.value)}
          />
          
          <Switch
            label="Active"
            checked={isActive}
            onChange={(e) => setIsActive(e.currentTarget.checked)}
          />
          
          <Group position="right">
            <Button variant="outline" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateAlert}>
              Create Alert
            </Button>
          </Group>
        </Stack>
      </Modal>
      
      {/* Edit Alert Modal */}
      <Modal
        opened={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Edit Price Alert"
        size="lg"
      >
        <Stack spacing="md">
          <Select
            label="Category"
            placeholder="Select a category"
            data={categories}
            value={category}
            onChange={(val) => setCategory(val || '')}
            required
          />
          
          <NumberInput
            label="Maximum Price"
            placeholder="Enter maximum price"
            value={maxPrice}
            onChange={(val) => setMaxPrice(val || 0)}
            min={0}
            required
          />
          
          <MultiSelect
            label="Keywords"
            placeholder="Enter keywords to match"
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
          
          <TextInput
            label="Email"
            placeholder="Enter notification email"
            value={email}
            onChange={(e) => setEmail(e.currentTarget.value)}
            required
          />
          
          <TextInput
            label="Webhook URL (Optional)"
            placeholder="Enter webhook URL for notifications"
            value={webhook}
            onChange={(e) => setWebhook(e.currentTarget.value)}
          />
          
          <Switch
            label="Active"
            checked={isActive}
            onChange={(e) => setIsActive(e.currentTarget.checked)}
          />
          
          <Group position="right">
            <Button variant="outline" onClick={() => setEditModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleEditAlert}>
              Save Changes
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}; 