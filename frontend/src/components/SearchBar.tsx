import React from 'react';
import { TextInput, ActionIcon, Group } from '@mantine/core';
import { IconSearch, IconX } from '@tabler/icons-react';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onClear: () => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({ value, onChange, onClear }) => {
  return (
    <Group>
      <TextInput
        placeholder="Search listings..."
        value={value}
        onChange={(e) => onChange(e.currentTarget.value)}
        icon={<IconSearch size={16} />}
        rightSection={
          value && (
            <ActionIcon onClick={onClear}>
              <IconX size={16} />
            </ActionIcon>
          )
        }
        style={{ flex: 1 }}
      />
    </Group>
  );
};
