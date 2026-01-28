import React from 'react';
import { Save, RefreshCw, FileText } from 'lucide-react';

interface HeaderProps {
  fileName: string | null;
  isModified: boolean;
  isSaving: boolean;
  lastSaved: Date | null;
  onSave: () => void;
  onRefresh: () => void;
}

export default function Header({ 
  fileName, 
  isModified, 
  isSaving, 
  lastSaved, 
  onSave, 
  onRefresh 
}: HeaderProps) {
  const formatLastSaved = (date: Date | null): string => {
    if (!date) return '';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 60000) {
      return '刚刚保存';
    } else if (diff < 3600000) {
      return `${Math.floor(diff / 60000)} 分钟前保存`;
    } else {
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      });
    }
  };

  return (
    <div style={{
      height: '50px',
      backgroundColor: '#323233',
      borderBottom: '1px solid #252526',
      display: 'flex',
      alignItems: 'center',
      padding: '0 16px',
      justifyContent: 'space-between',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <FileText size={20} style={{ color: '#4ec9b0' }} />
        <div style={{ fontSize: '14px', color: '#cccccc' }}>
          {fileName || '未选择文件'}
          {isModified && (
            <span style={{ marginLeft: '8px', color: '#cca700' }}>
              (未保存)
            </span>
          )}
        </div>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {lastSaved && (
          <span style={{ 
            fontSize: '12px', 
            color: '#858585',
            marginRight: '8px'
          }}>
            {formatLastSaved(lastSaved)}
          </span>
        )}
        
        <button
          onClick={onRefresh}
          style={{
            padding: '6px 12px',
            backgroundColor: '#0e639c',
            color: 'white',
            border: 'none',
            borderRadius: '3px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '13px',
            transition: 'background-color 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#1177bb';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#0e639c';
          }}
        >
          <RefreshCw size={14} />
          刷新
        </button>
        
        <button
          onClick={onSave}
          disabled={!isModified || isSaving}
          style={{
            padding: '6px 12px',
            backgroundColor: isModified ? '#0e639c' : '#3c3c3c',
            color: 'white',
            border: 'none',
            borderRadius: '3px',
            cursor: isModified && !isSaving ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '13px',
            opacity: isModified && !isSaving ? 1 : 0.6,
            transition: 'background-color 0.2s',
          }}
          onMouseEnter={(e) => {
            if (isModified && !isSaving) {
              e.currentTarget.style.backgroundColor = '#1177bb';
            }
          }}
          onMouseLeave={(e) => {
            if (isModified && !isSaving) {
              e.currentTarget.style.backgroundColor = '#0e639c';
            }
          }}
        >
          <Save size={14} />
          {isSaving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  );
}
