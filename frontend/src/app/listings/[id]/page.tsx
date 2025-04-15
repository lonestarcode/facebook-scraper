'use client';

import { ListingDetail } from '@/components/ListingDetail';
import { useParams } from 'next/navigation';

export default function ListingPage() {
  const params = useParams();
  const id = params.id as string;
  
  return <ListingDetail id={id} />;
} 