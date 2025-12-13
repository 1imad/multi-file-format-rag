import { useState, useRef } from 'react';
import { MdClose, MdCloudUpload, MdCheckCircle, MdError } from 'react-icons/md';
import { IoDocument } from 'react-icons/io5';
import './UploadModal.css';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: () => void;
  apiUrl?: string;
  token: string;
}

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

export default function UploadModal({ isOpen, onClose, onUploadSuccess, apiUrl = 'http://localhost:8000', token }: UploadModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [uploadResult, setUploadResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadStatus('idle');
      setErrorMessage('');
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadStatus('idle');
      setErrorMessage('');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploadStatus('uploading');
    setUploadProgress(0);
    setErrorMessage('');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) return prev;
          return prev + 10;
        });
      }, 200);

      const response = await fetch(`${apiUrl}/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      setUploadProgress(100);
      setUploadStatus('success');
      setUploadResult(data);
      onUploadSuccess();

      // Auto-close after success
      setTimeout(() => {
        handleClose();
      }, 2000);
    } catch (error: any) {
      console.error('Upload error:', error);
      setUploadStatus('error');
      setErrorMessage(error.message || 'Failed to upload file');
      setUploadProgress(0);
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    setUploadStatus('idle');
    setUploadProgress(0);
    setErrorMessage('');
    setUploadResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    onClose();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  if (!isOpen) return null;

  return (
    <div className="upload-modal-overlay" onClick={handleClose}>
      <div className="upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="upload-modal-header">
          <h3>Upload Document</h3>
          <button className="btn-close-modal" onClick={handleClose}>
            <MdClose />
          </button>
        </div>

        <div className="upload-modal-body">
          {!selectedFile ? (
            <div
              className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <MdCloudUpload size={64} />
              <p className="dropzone-title">Drag & drop your file here</p>
              <p className="dropzone-subtitle">or click to browse</p>
              <p className="dropzone-formats">
                Supported: PDF, TXT, MD, EPUB, HTML, DOC, DOCX
              </p>
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileSelect}
                accept=".pdf,.txt,.md,.epub,.html,.doc,.docx"
                style={{ display: 'none' }}
              />
            </div>
          ) : (
            <div className="upload-file-selected">
              <div className="selected-file-info">
                <IoDocument size={48} />
                <div className="file-details">
                  <h4>{selectedFile.name}</h4>
                  <p>{formatFileSize(selectedFile.size)}</p>
                </div>
              </div>

              {uploadStatus === 'uploading' && (
                <div className="upload-progress-container">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                  <p className="progress-text">{uploadProgress}% uploaded</p>
                </div>
              )}

              {uploadStatus === 'success' && uploadResult && (
                <div className="upload-status success">
                  <MdCheckCircle size={32} />
                  <h4>Upload Successful!</h4>
                  <div className="upload-details">
                    <p><strong>Filename:</strong> {uploadResult.filename}</p>
                    <p><strong>Content Length:</strong> {uploadResult.content_length} characters</p>
                    <p><strong>Model:</strong> {uploadResult.embedding_model}</p>
                  </div>
                </div>
              )}

              {uploadStatus === 'error' && (
                <div className="upload-status error">
                  <MdError size={32} />
                  <h4>Upload Failed</h4>
                  <p>{errorMessage}</p>
                </div>
              )}

              {uploadStatus === 'idle' && (
                <button className="btn-change-file" onClick={() => setSelectedFile(null)}>
                  Choose Different File
                </button>
              )}
            </div>
          )}
        </div>

        <div className="upload-modal-footer">
          <button
            className="btn btn-cancel"
            onClick={handleClose}
            disabled={uploadStatus === 'uploading'}
          >
            Cancel
          </button>
          <button
            className="btn btn-upload-primary"
            onClick={handleUpload}
            disabled={!selectedFile || uploadStatus === 'uploading' || uploadStatus === 'success'}
          >
            {uploadStatus === 'uploading' ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </div>
    </div>
  );
}
