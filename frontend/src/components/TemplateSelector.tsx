import { useEffect, useState } from 'react';
import { Search, Upload } from 'lucide-react';
import { motion } from 'framer-motion';

export interface Template {
  id: number;
  name: string;
  image_url?: string;
  text_field_count: number;
  text_coordinates: number[][];
  preview_image_url?: string;
  font_path: string;
  usage_instructions?: string;
}

export interface TemplateSelectorProps {
  onSelectTemplate: (template: Template) => void;
  selectedTemplateId?: number;
}

export function TemplateSelector({
  onSelectTemplate,
  selectedTemplateId,
}: TemplateSelectorProps) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<Template[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch templates from backend on mount
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        setIsLoading(true);
        const response = await fetch('/api/memes/templates');
        if (!response.ok) {
          throw new Error(`Failed to fetch templates: ${response.statusText}`);
        }
        const data = await response.json();
        setTemplates(data);
        setFilteredTemplates(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load templates');
      } finally {
        setIsLoading(false);
      }
    };

    fetchTemplates();
  }, []);

  // Handle search filter
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredTemplates(templates);
    } else {
      const query = searchQuery.toLowerCase();
      setFilteredTemplates(
        templates.filter((t) =>
          t.name.toLowerCase().includes(query)
        )
      );
    }
  }, [searchQuery, templates]);

  return (
    <div className="card-dark">
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-4">Meme Templates</h3>

        {/* Search Bar */}
        <div className="relative">
          <Search size={18} className="absolute left-3 top-3 text-muted" />
          <input
            type="text"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-dark pl-10 w-full"
          />
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center items-center py-12">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-acid border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-secondary text-sm">Loading templates...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <p className="text-red-500 text-sm">{error}</p>
        </div>
      )}

      {/* Template Grid */}
      {!isLoading && !error && (
        <>
          {filteredTemplates.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-secondary mb-2">No templates found</p>
              <p className="text-muted text-sm">Try searching with different keywords</p>
            </div>
          ) : (
            <motion.div
              className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
            >
              {filteredTemplates.map((template, idx) => (
                <motion.button
                  key={template.id}
                  onClick={() => onSelectTemplate(template)}
                  className={`group relative rounded-lg overflow-hidden border-2 transition-all aspect-square ${
                    selectedTemplateId === template.id
                      ? 'border-acid ring-2 ring-acid'
                      : 'border-border hover:border-acid/50'
                  }`}
                  whileHover={{ scale: 1.05 }}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                >
                  {/* Template Image */}
                  <img
                    src={template.image_url || template.preview_image_url}
                    alt={template.name}
                    className="w-full h-full object-cover group-hover:brightness-110 transition-all"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />

                  {/* Placeholder if image fails */}
                  <div className="absolute inset-0 bg-surface-2 flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-3xl mb-1">🖼️</div>
                      <p className="text-xs text-secondary">{template.name}</p>
                    </div>
                  </div>

                  {/* Overlay Info */}
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-all flex flex-col justify-end p-2">
                    <p className="text-xs font-semibold text-white truncate">
                      {template.name}
                    </p>
                    <p className="text-xs text-gray-300">
                      {template.text_field_count} text field{
                        template.text_field_count !== 1 ? 's' : ''
                      }
                    </p>
                    {template.usage_instructions && (
                      <p className="text-[10px] text-gray-300 mt-1 line-clamp-2">
                        {template.usage_instructions}
                      </p>
                    )}
                  </div>

                  {/* Selected Checkmark */}
                  {selectedTemplateId === template.id && (
                    <div className="absolute top-2 right-2 bg-acid rounded-full w-6 h-6 flex items-center justify-center">
                      <span className="text-black text-sm font-bold">✓</span>
                    </div>
                  )}
                </motion.button>
              ))}
            </motion.div>
          )}

          {/* Results Count */}
          <p className="text-xs text-muted mt-4">
            Showing {filteredTemplates.length} of {templates.length} templates
          </p>
        </>
      )}

      {/* Custom Upload (Optional Future Feature) */}
      {!isLoading && !error && (
        <div className="mt-6 pt-6 border-t border-border">
          <button
            className="btn-ghost w-full justify-center gap-2"
            disabled
            title="Custom uploads coming soon"
          >
            <Upload size={16} />
            Upload Custom Template
          </button>
          <p className="text-xs text-muted text-center mt-2">Coming soon</p>
        </div>
      )}
    </div>
  );
}
