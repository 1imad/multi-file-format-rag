import { useState, useEffect } from 'react';
import { MdDelete, MdRefresh, MdInsertDriveFile, MdUpload } from 'react-icons/md';
import './FileList.css';

interface FileInfo {
  filename: string;
  content_type: string | null;
  file_size: number | null;
  file_path: string;
  chunk_count: number;
}

interface FileListProps {
  apiUrl?: string;
  token: string;
  onFileDeleted?: () => void;
  onUploadClick?: () => void;
}

export default function FileList({ apiUrl = 'http://localhost:8000', token, onFileDeleted, onUploadClick }: FileListProps) {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/files`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        if (response.status === 401) {
          setError('Session expired. Please refresh the page and login again.');
          return;
        }
        throw new Error(`Failed to fetch files: ${response.statusText}`);
      }
      const data = await response.json();
      setFiles(data.files || []);
    } catch (err: any) {
      setError(err.message);
      console.error('Error fetching files:', err);
    } finally {
      setLoading(false);
    }
  };

  const deleteFile = async (filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"? This will remove all embeddings for this file.`)) {
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/files/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to delete file: ${response.statusText}`);
      }

      // Remove from local state
      setFiles(files.filter(f => f.filename !== filename));
      
      // Notify parent component
      if (onFileDeleted) {
        onFileDeleted();
      }
    } catch (err: any) {
      setError(err.message);
      console.error('Error deleting file:', err);
    }
  };

  const formatFileSize = (bytes: number | null): string => {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  return (
    <div className="file-list-container">
      <div className="file-list-header">
        <h3>Uploaded Files</h3>
        <div className="file-list-header-actions">
          <button 
            className="btn-upload-file"
            onClick={onUploadClick}
            title="Upload document"
          >
            <MdUpload />
          </button>
          <button 
            className="btn-refresh" 
            onClick={fetchFiles}
            disabled={loading}
            title="Refresh file list"
          >
            <MdRefresh className={loading ? 'spinning' : ''} />
          </button>
        </div>
      </div>

      {error && (
        <div className="file-list-error">
          <p>⚠️ {error}</p>
        </div>
      )}

      <div className="file-list">
        {loading && files.length === 0 ? (
          <div className="file-list-loading">
            <p>Loading files...</p>
          </div>
        ) : files.length === 0 ? (
          <div className="file-list-empty">
            <MdInsertDriveFile size={48} />
            <p>No files uploaded yet</p>
          </div>
        ) : (
          files.map((file) => (
            <div key={file.filename} className="file-item">
              <div className="file-item-icon">
                <MdInsertDriveFile />
              </div>
              <div className="file-item-info">
                <div className="file-item-name" title={file.filename}>
                  {file.filename}
                </div>
                <div className="file-item-meta">
                  <span>{formatFileSize(file.file_size)}</span>
                  <span>•</span>
                  <span>{file.chunk_count} chunks</span>
                </div>
              </div>
              <button
                className="btn-delete-file"
                onClick={() => deleteFile(file.filename)}
                title={`Delete ${file.filename}`}
              >
                <MdDelete />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
