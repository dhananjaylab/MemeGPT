import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { Toaster } from 'react-hot-toast';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Providers } from '@/components/Providers';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'MemeGPT - AI Meme Generator',
  description: 'Generate hilarious memes with AI. Powered by GPT-4o with 50+ templates.',
  keywords: ['meme', 'generator', 'AI', 'GPT', 'funny', 'viral', 'social media'],
  authors: [{ name: 'MemeGPT Team' }],
  creator: 'MemeGPT',
  publisher: 'MemeGPT',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://memegpt.ai',
    title: 'MemeGPT - AI Meme Generator',
    description: 'Generate hilarious memes with AI. Powered by GPT-4o with 50+ templates.',
    siteName: 'MemeGPT',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'MemeGPT - AI Meme Generator',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'MemeGPT - AI Meme Generator',
    description: 'Generate hilarious memes with AI. Powered by GPT-4o with 50+ templates.',
    images: ['/og-image.png'],
    creator: '@memegpt',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  verification: {
    google: 'your-google-verification-code',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>
          <div className="relative flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
          <Toaster
            position="bottom-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: 'hsl(var(--surface))',
                color: 'hsl(var(--foreground))',
                border: '1px solid hsl(var(--border))',
              },
              success: {
                iconTheme: {
                  primary: '#B8FF00',
                  secondary: 'black',
                },
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}