
import { GoogleGenAI, Type } from "@google/genai";
import type { MemeTemplate } from '../types';

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || '' });

export async function synthesizeMemeCaptions(prompt: string, templates: MemeTemplate[]) {
  if (!process.env.GEMINI_API_KEY) {
    throw new Error("Neural interface offline. (API Key missing)");
  }
  const templateContext = templates.map(t => ({
    id: t.id,
    name: t.name,
    description: t.description,
    textFields: t.textFields
  }));

  const response = await ai.models.generateContent({
    model: "gemini-3-flash-preview",
    contents: `Analyze this prompt and pick the 5 best diverse meme templates and generate captions for each: "${prompt}"
    
    Templates available: ${JSON.stringify(templateContext)}`,
    config: {
      systemInstruction: "You are MemeGPT, an expert meme synthesizer. Choose the 5 most appropriate and diverse templates from the provided list. Return an array of options. Each option must have a templateId and a captions list matching that template's textFields count.",
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.OBJECT,
        properties: {
          options: {
            type: Type.ARRAY,
            items: {
              type: Type.OBJECT,
              properties: {
                templateId: { type: Type.STRING },
                captions: { type: Type.ARRAY, items: { type: Type.STRING } },
                reasoning: { type: Type.STRING }
              },
              required: ["templateId", "captions"]
            }
          }
        },
        required: ["options"]
      }
    }
  });

  try {
    const result = JSON.parse(response.text);
    return result.options as { templateId: string; captions: string[]; reasoning: string }[];
  } catch (error) {
    console.error("Failed to parse Gemini response:", error);
    throw new Error("Meme synthesis failed to decode neural patterns.");
  }
}
