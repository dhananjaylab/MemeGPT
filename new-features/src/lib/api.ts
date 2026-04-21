
import { 
  collection, 
  addDoc, 
  getDocs, 
  query, 
  where, 
  orderBy, 
  limit, 
  serverTimestamp,
  doc,
  getDoc,
  updateDoc,
  increment
} from 'firebase/firestore';
import { db, auth } from './firebase';
import type { GeneratedMeme, TrendingTopic, User, MemeTemplate, MemeSettings } from '../types';

export class MemeAPI {
  private static MEMES_COLLECTION = 'memes';
  private static TEMPLATES_COLLECTION = 'templates';

  static async generate(prompt: string, templateId: string, text: string[], settings: MemeSettings): Promise<GeneratedMeme> {
    const memeData = {
      user_id: null,
      prompt,
      template_id: templateId,
      template_name: settings.templateName || 'Custom',
      meme_text: text,
      image_url: settings.imageUrl, // The synthesized URL
      created_at: serverTimestamp(),
      like_count: 0,
      share_count: 0,
      view_count: 1,
      is_public: true
    };

    try {
      const docRef = await addDoc(collection(db, this.MEMES_COLLECTION), memeData);
      
      return {
        id: docRef.id,
        ...memeData,
        created_at: new Date().toISOString()
      } as any;
    } catch (error: any) {
      console.error("Firestore Save Error:", error);
      if (error.message?.includes('insufficient permissions')) {
        throw new Error("Security check failed. Are you signed in?");
      }
      if (error.message?.includes('larger than the maximum')) {
        throw new Error("Synthesis payload too heavy. Try shorter text.");
      }
      throw new Error(`Cloud sync failed: ${error.message}`);
    }
  }

  static async getAll(): Promise<GeneratedMeme[]> {
    const q = query(
      collection(db, this.MEMES_COLLECTION), 
      where('is_public', '==', true),
      orderBy('created_at', 'desc'),
      limit(50)
    );
    const querySnapshot = await getDocs(q);
    return querySnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      created_at: doc.data().created_at?.toDate()?.toISOString() || new Date().toISOString()
    })) as GeneratedMeme[];
  }

  static async getMyMemes(): Promise<GeneratedMeme[]> {
    const user = auth.currentUser;
    if (!user) return [];

    const q = query(
      collection(db, this.MEMES_COLLECTION), 
      where('user_id', '==', user.uid),
      orderBy('created_at', 'desc')
    );
    const querySnapshot = await getDocs(q);
    return querySnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      created_at: doc.data().created_at?.toDate()?.toISOString() || new Date().toISOString()
    })) as GeneratedMeme[];
  }

  static async getTemplates(): Promise<MemeTemplate[]> {
    // For now, return hardcoded, but in a real app this would be in Firestore
    return [
      { id: '1', name: 'Distracted Boyfriend', url: 'https://picsum.photos/seed/meme1/600/600', description: 'Man looking at another woman', textFields: 3 },
      { id: '2', name: 'Drake Hotline Bling', url: 'https://picsum.photos/seed/meme2/600/600', description: 'Drake approving/disapproving', textFields: 2 },
      { id: '3', name: 'Two Buttons', url: 'https://picsum.photos/seed/meme3/600/600', description: 'Hard choice between two buttons', textFields: 2 },
      { id: '4', name: 'Change My Mind', url: 'https://picsum.photos/seed/meme4/600/600', description: 'Steven Crowder at a table', textFields: 1 },
      { id: '5', name: 'Batman Slapping Robin', url: 'https://picsum.photos/seed/meme5/600/600', description: 'Batman slapping Robin', textFields: 2 },
    ];
  }

  static async getTrending(): Promise<TrendingTopic[]> {
    return [
      { id: '1', title: 'Silicon Valley layoffs', source: 'news', score: 45000, created_at: '' },
      { id: '2', title: 'Why TypeScript is winning', source: 'reddit', score: 12000, created_at: '' },
      { id: '3', title: 'MemeGPT goes viral', source: 'twitter', score: 89000, created_at: '' },
    ];
  }

  static async incrementMetric(memeId: string, metric: 'like_count' | 'share_count' | 'view_count'): Promise<void> {
    const docRef = doc(db, this.MEMES_COLLECTION, memeId);
    await updateDoc(docRef, {
      [metric]: increment(1)
    });
  }
}
