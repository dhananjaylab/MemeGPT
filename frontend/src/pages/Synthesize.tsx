import { MemeGenerator } from '../components/MemeGenerator';

export function Synthesize() {
  return (
    <div className="space-y-6 py-6">
      <div>
        <h1 className="text-4xl font-bold">Synthesize</h1>
        <p className="text-secondary mt-2">
          Generate memes with AI suggestions or manual editing.
        </p>
      </div>
      <MemeGenerator />
    </div>
  );
}
