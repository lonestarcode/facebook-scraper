# Facebook Marketplace Scraper Frontend

A modern Next.js application for visualizing and interacting with Facebook Marketplace listings from the scraper backend.

## Features

- View and filter Facebook Marketplace listings
- Search and sort listings by various criteria
- Real-time updates via WebSockets
- Set up price alerts for specific items
- Detailed listing view with analysis
- Mobile-friendly responsive design

## Tech Stack

- **Framework**: Next.js 13 (App Router)
- **UI Library**: Mantine UI
- **State Management**: React Hooks and Context
- **Data Fetching**: SWR
- **Real-time Updates**: WebSockets
- **Icons**: Tabler Icons
- **TypeScript**: For type safety

## Getting Started

### Prerequisites

- Node.js 16+ 
- Yarn or npm

### Installation

1. Install dependencies:

```bash
npm install
# or
yarn install
```

2. Set up environment variables (create a `.env.local` file):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### Development

Run the development server:

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the application.

### Building for Production

```bash
npm run build
# or
yarn build
```

## Project Structure

- `src/app/` - Next.js App Router pages and layouts
- `src/components/` - Reusable React components
- `src/hooks/` - Custom React hooks
- `src/lib/` - Utility functions and API clients
- `src/types/` - TypeScript type definitions

## Integration with Backend

The frontend communicates with the backend through:

1. RESTful API endpoints for CRUD operations
2. WebSocket connections for real-time updates

Make sure the backend server is running on the URL specified in your environment variables.

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add some amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request 