import { Metadata } from 'next';
import { DashboardClient } from './DashboardClient';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export const metadata: Metadata = {
  title: 'Dashboard | MemeGPT',
  description: 'Manage your generated memes and API access.',
};

export default function DashboardPage() {
  // In a real app, we would get the session here
  // const session = await getServerSession(authOptions);
  
  return (
    <main className="container mx-auto px-4 py-12 max-w-6xl">
      <div className="mb-10">
        <h1 className="font-display text-4xl font-bold text-primary mb-2">
          Dashboard
        </h1>
        <p className="font-mono text-sm text-muted uppercase tracking-widest">
          Control center for your AI meme factory
        </p>
      </div>

      <ErrorBoundary componentName="Dashboard">
        <DashboardClient />
      </ErrorBoundary>
    </main>
  );
}
