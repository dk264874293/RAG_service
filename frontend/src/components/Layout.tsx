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
    <div className="h-screen flex flex-col bg-editor-bg text-editor-text overflow-hidden">
      <Header
        fileName={currentFile?.name || null}
        isModified={editorState.isModified}
        isSaving={editorState.isSaving}
        lastSaved={editorState.lastSaved}
        onSave={onSave}
        onRefresh={onRefresh}
      />

      <div className="flex-1 flex overflow-hidden">
        <div className="w-[300px] border-r border-editor-border bg-editor-sidebar flex flex-col">
          <FileList
            files={files}
            currentFile={currentFile}
            onFileSelect={onFileSelect}
            loading={loading}
          />
        </div>

        <div className="flex-1 flex flex-col bg-editor-bg">
          <div className="flex-1 flex overflow-hidden">
            <div className="flex-1 border-r border-editor-border flex flex-col">
              <div className="px-4 py-2 bg-[#2d2d30] border-b border-[#3e3e42] text-xs text-editor-textMuted uppercase tracking-wider">
                编辑器
              </div>
              <div className="flex-1 overflow-hidden">
                <MonacoEditor
                  value={editorState.content}
                  onChange={onContentChange}
                  height="100%"
                />
              </div>
            </div>

            <div className="w-[400px] flex flex-col">
              <div className="px-4 py-2 bg-[#2d2d30] border-b border-[#3e3e42] text-xs text-editor-textMuted uppercase tracking-wider">
                预览
              </div>
              <div className="flex-1 overflow-hidden">
                <MarkdownPreview content={editorState.content} />
              </div>
            </div>
          </div>

          {editorState.error && (
            <div className="px-4 py-2 bg-[#5a1d1d] text-[#ff6b68] text-sm flex items-center">
              {editorState.error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
