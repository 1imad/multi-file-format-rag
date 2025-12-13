import { useState, useEffect } from 'react';
import { IoClose, IoSave, IoRefresh } from 'react-icons/io5';
import './SettingsModal.css';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (settings: SettingsData) => void;
  currentSettings: SettingsData;
}

export interface SettingsData {
  backendUrl: string;
  embeddingModel: string;
  llmModel: string;
}

export default function SettingsModal({ isOpen, onClose, onSave, currentSettings }: SettingsModalProps) {
  const [settings, setSettings] = useState<SettingsData>(currentSettings);

  useEffect(() => {
    setSettings(currentSettings);
  }, [currentSettings, isOpen]);

  const handleSave = () => {
    onSave(settings);
    onClose();
  };

  const handleReset = () => {
    const defaultSettings: SettingsData = {
      backendUrl: 'http://localhost:8000',
      embeddingModel: 'text-embedding-3-small',
      llmModel: 'gpt-4o-mini',
    };
    setSettings(defaultSettings);
  };

  if (!isOpen) return null;

  return (
    <div className="settings-modal-overlay" onClick={onClose}>
      <div className="settings-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="settings-modal-header">
          <h2>Settings</h2>
          <button className="btn-close-settings" onClick={onClose} title="Close">
            <IoClose />
          </button>
        </div>

        <div className="settings-modal-body">
          <div className="settings-group">
            <label htmlFor="backend-url">Backend URL</label>
            <input
              id="backend-url"
              type="text"
              value={settings.backendUrl}
              onChange={(e) => setSettings({ ...settings, backendUrl: e.target.value })}
              placeholder="http://localhost:8000"
            />
            <span className="settings-help">The URL of your backend API server</span>
          </div>

          <div className="settings-group">
            <label htmlFor="embedding-model">Embedding Model</label>
            <input
              id="embedding-model"
              type="text"
              value={settings.embeddingModel}
              onChange={(e) => setSettings({ ...settings, embeddingModel: e.target.value })}
              placeholder="text-embedding-3-small"
            />
            <span className="settings-help">OpenAI embedding model for document processing</span>
          </div>

          <div className="settings-group">
            <label htmlFor="llm-model">LLM Model</label>
            <input
              id="llm-model"
              type="text"
              value={settings.llmModel}
              onChange={(e) => setSettings({ ...settings, llmModel: e.target.value })}
              placeholder="gpt-4o-mini"
            />
            <span className="settings-help">OpenAI model for chat responses</span>
          </div>
        </div>

        <div className="settings-modal-footer">
          <button className="btn-reset" onClick={handleReset}>
            <IoRefresh />
            Reset to Defaults
          </button>
          <div className="settings-actions">
            <button className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button className="btn-save" onClick={handleSave}>
              <IoSave />
              Save Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
