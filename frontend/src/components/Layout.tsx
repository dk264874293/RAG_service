import React from 'react';
import Header from './Header';
import FileList from './FileList';
import MonacoEditor from './MonacoEditor';
import MarkdownPreview from './MarkdownPreview';

interface LayoutProps {
  files: any[];
  currentFile: any;
  editorState: any;
  onFileSelect: (file: any) => void;
  onSave: () => void;
  onRefresh: () => void;
  onContentChange: (value: string | undefined) => void;
  loading: boolean;
}

export default function Layout({
  files,
  currentFile,
  editorState,
  onFileSelect,
  onSave,
  onRefresh,
  onContentChange,
  loading,
}: LayoutProps) {
  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#1e1e1e',
      color: '#cccccc',
      overflow: 'hidden',
    }}>
      <Header
        fileName={currentFile?.name || null}
        isModified={editorState.isModified}
        isSaving={editorState.isSaving}
        lastSaved={editorState.lastSaved}
        onSave={onSave}
        onRefresh={onRefresh}
      />
      
      <div style={{
        flex: 1,
        display: 'flex',
        overflow: 'hidden',
      }}>
        <div style={{
          width: '300px',
          borderRight: '1px solid #252526',
          backgroundColor: '#252526',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <FileList
            files={files}
            currentFile={currentFile}
            onFileSelect={onFileSelect}
            loading={loading}
          />
        </div>
        
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#1e1e1e',
        }}>
          <div style={{
            flex: 1,
            display: 'flex',
            overflow: 'hidden',
          }}>
            <div style={{
              flex: 1,
              borderRight: '1px solid #333333',
              display: 'flex',
              flexDirection: 'column',
            }}>
              <div style={{
                padding: '8px 16px',
                backgroundColor: '#2d2d30',
                borderBottom: '1px solid #3e3e42',
                fontSize: '12px',
                color: '#858585',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                编辑器
              </div>
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <MonacoEditor
                  value={editorState.content}
                  onChange={onContentChange}
                  height="100%"
                />
              </div>
            </div>
            
            <div style={{
              width: '400px',
              display: 'flex',
              flexDirection: 'column',
            }}>
              <div style={{
                padding: '8px 16px',
                backgroundColor: '#2d2d30',
                borderBottom: '1px solid #3e3e42',
                fontSize: '12px',
                color: '#858585',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}>
                预览
              </div>
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <MarkdownPreview content={editorState.content} />
              </div>
            </div>
          </div>
          
          {editorState.error && (
            <div style={{
              padding: '8px 16px',
              backgroundColor: '#5a1d1d',
              color: '#ff6b68',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
            }}>
              {editorState.error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
