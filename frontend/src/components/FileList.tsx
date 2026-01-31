import { File, FileText, Clock } from 'lucide-react';
import { MarkdownFile } from '../types';

interface FileListProps {
  files: MarkdownFile[];
  currentFile: MarkdownFile | null;
  onFileSelect: (file: MarkdownFile) => void;
  loading: boolean;
}

export default function FileList({ files, currentFile, onFileSelect, loading }: FileListProps) {
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatTime = (isoTime: string): string => {
    const date = new Date(isoTime);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="p-5 text-center text-editor-textMuted">加载中...</div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="p-5 text-center text-gray-600">暂无Markdown文件</div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-4 border-b border-[#333] bg-editor-sidebar text-editor-text">
        <h3 className="text-sm font-medium">文件列表 ({files.length})</h3>
      </div>
      <div className="flex-1 overflow-auto p-2 scrollbar-thin">
        {files.map((file) => (
          <div
            key={file.path}
            onClick={() => onFileSelect(file)}
            className={`p-2.5 mb-1 rounded cursor-pointer border transition-all duration-200 ${
              currentFile?.path === file.path
                ? 'bg-[#37373d] border-[#007acc]'
                : 'border-transparent bg-transparent hover:bg-[#2a2d2e]'
            }`}
          >
            <div className="flex items-center mb-1">
              <FileText size={16} className="mr-2 text-[#4ec9b0] flex-shrink-0" />
              <span className="text-sm text-editor-text overflow-hidden text-ellipsis whitespace-nowrap flex-1">
                {file.name}
              </span>
            </div>
            <div className="text-xs text-editor-textMuted ml-6 space-y-1">
              <div className="flex items-center">
                <File size={12} className="mr-1 flex-shrink-0" />
                <span className="overflow-hidden text-ellipsis whitespace-nowrap max-w-[200px]">
                  {file.folder_name}
                </span>
              </div>
              <div className="flex items-center">
                <Clock size={12} className="mr-1 flex-shrink-0" />
                <span>{formatTime(file.modified_time)}</span>
                <span className="mx-2">|</span>
                <span>{formatFileSize(file.size)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
