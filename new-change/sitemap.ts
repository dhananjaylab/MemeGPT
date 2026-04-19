import type { MetadataRoute } from "next";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "https://memegpt.app";
const API_URL = process.env.API_URL ?? "http://localhost:8000";

export const dynamic = "force-dynamic";
export const revalidate = 3600; // regenerate every hour

async function getRecentMemeIds(): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/api/memes?page=1&limit=100`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.memes ?? []).map((m: { id: string }) => m.id);
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const memeIds = await getRecentMemeIds();

  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: APP_URL,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${APP_URL}/gallery`,
      lastModified: new Date(),
      changeFrequency: "hourly",
      priority: 0.9,
    },
    {
      url: `${APP_URL}/api-docs`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.7,
    },
  ];

  const memeRoutes: MetadataRoute.Sitemap = memeIds.map((id) => ({
    url: `${APP_URL}/meme/${id}`,
    lastModified: new Date(),
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));

  return [...staticRoutes, ...memeRoutes];
}
