import React from 'react';
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
      <div style={{ padding: '20px', textAlign: 'center' }}>加载中...</div>
    );
  }

  if (files.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
        暂无Markdown文件
      </div>
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ 
        padding: '16px', 
        borderBottom: '1px solid #333', 
        backgroundColor: '#252526',
        color: '#cccccc'
      }}>
        <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 500 }}>
          文件列表 ({files.length})
        </h3>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '8px' }}>
        {files.map((file) => (
          <div
            key={file.path}
            onClick={() => onFileSelect(file)}
            style={{
              padding: '10px',
              marginBottom: '4px',
              borderRadius: '4px',
              cursor: 'pointer',
              backgroundColor: currentFile?.path === file.path ? '#37373d' : 'transparent',
              border: currentFile?.path === file.path ? '1px solid #007acc' : '1px solid transparent',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              if (currentFile?.path !== file.path) {
                e.currentTarget.style.backgroundColor = '#2a2d2e';
              }
            }}
            onMouseLeave={(e) => {
              if (currentFile?.path !== file.path) {
                e.currentTarget.style.backgroundColor = 'transparent';
              }
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
              <FileText size={16} style={{ marginRight: '8px', color: '#4ec9b0' }} />
              <span style={{ 
                fontSize: '13px', 
                color: '#cccccc',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                flex: 1
              }}>
                {file.name}
              </span>
            </div>
            <div style={{ fontSize: '11px', color: '#858585', marginLeft: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2px' }}>
                <File size={12} style={{ marginRight: '4px' }} />
                <span style={{ 
                  overflow: 'hidden', 
                  textOverflow: 'ellipsis', 
                  whiteSpace: 'nowrap',
                  maxWidth: '200px'
                }}>
                  {file.folder_name}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <Clock size={12} style={{ marginRight: '4px' }} />
                <span>{formatTime(file.modified_time)}</span>
                <span style={{ marginLeft: '8px', marginRight: '8px' }}>|</span>
                <span>{formatFileSize(file.size)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
