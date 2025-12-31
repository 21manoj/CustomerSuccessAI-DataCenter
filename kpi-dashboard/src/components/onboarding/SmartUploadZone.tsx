import React, { useCallback, useState } from 'react';
import { Upload, FileText, X } from 'lucide-react';

interface SmartUploadZoneProps {
  onFileSelect: (file: File) => void;
  acceptedFormats?: string[];
  maxSizeBytes?: number;
  showPreview?: boolean;
}

const SmartUploadZone: React.FC<SmartUploadZoneProps> = ({
  onFileSelect,
  acceptedFormats = ['.csv', '.xlsx', '.xls'],
  maxSizeBytes = 10 * 1024 * 1024, // 10MB
  showPreview = true
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const validateFile = (file: File): string | null => {
    // Check file size
    if (file.size > maxSizeBytes) {
      return `File size exceeds ${Math.round(maxSizeBytes / 1024 / 1024)}MB limit`;
    }

    // Check file extension
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedFormats.includes(extension)) {
      return `File format not supported. Accepted formats: ${acceptedFormats.join(', ')}`;
    }

    return null;
  };

  const handleFile = useCallback(async (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setSelectedFile(file);
    onFileSelect(file);
  }, [onFileSelect, acceptedFormats, maxSizeBytes]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  }, [handleFile]);

  const removeFile = () => {
    setSelectedFile(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4 py-12">
      <div className="max-w-2xl w-full bg-white rounded-xl shadow-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">📤 Upload Your Customer Data</h2>

        {!selectedFile ? (
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
              isDragging
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-blue-400 bg-gray-50'
            }`}
          >
            <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-lg font-medium text-gray-900 mb-2">
              Drag your file here or click to browse
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Supports: {acceptedFormats.join(', ')}
            </p>
            <input
              type="file"
              accept={acceptedFormats.join(',')}
              onChange={handleFileInput}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer"
            >
              Choose File
            </label>
          </div>
        ) : (
          <div className="border border-gray-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <FileText className="h-8 w-8 text-blue-600" />
                <div>
                  <p className="font-medium text-gray-900">{selectedFile.name}</p>
                  <p className="text-sm text-gray-500">
                    {(selectedFile.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              <button
                onClick={removeFile}
                className="p-2 text-gray-400 hover:text-red-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm text-green-700">
                ✓ File selected and ready to upload
              </p>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <div className="mt-6 space-y-2 text-sm text-gray-600">
          <p className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            We'll automatically detect your columns
          </p>
          <p className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            Validate data quality in real-time
          </p>
          <p className="flex items-center gap-2">
            <span className="text-green-600">✓</span>
            Calculate health scores immediately
          </p>
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={() => {
              // Use sample data option
              console.log('Use sample data');
            }}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Don't have data yet? Use Sample Data to explore
          </button>
        </div>
      </div>
    </div>
  );
};

export default SmartUploadZone;

