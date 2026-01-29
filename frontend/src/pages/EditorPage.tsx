import React from 'react';
import { useMarkdownFiles } from '../hooks/useMarkdownFiles';
import { useDebounce } from '../hooks/useDebounce';
import MonacoEditor from '../components/MonacoEditor';
import MarkdownPreview from '../components/MarkdownPreview';
import FileList from '../components/FileList';

export default function EditorPage() {
  const {
    files,
    loading,
    editorState,
    loadFiles,
    loadFile,
    saveFile,
    updateContent,
  } = useMarkdownFiles();

  const debouncedContent = useDebounce(editorState.content, 2000);

  const handleFileSelect = async (file: any) => {
    await loadFile(file.path);
  };

  const handleSave = async () => {
    await saveFile();
  };

  const handleRefresh = async () => {
    await loadFiles();
  };

  const handleContentChange = (value: string | undefined) => {
    if (value !== undefined) {
      updateContent(value);
    }
  };

  React.useEffect(() => {
    if (editorState.isModified && debouncedContent !== editorState.currentFile?.content) {
      handleSave();
    }
  }, [debouncedContent]);

  return (
    <div className="flex h-screen">
      <div className="w-64 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
        <FileList
          files={files}
          currentFile={editorState.currentFile}
          onFileSelect={handleFileSelect}
          onRefresh={handleRefresh}
          loading={loading}
        />
      </div>

      <div className="flex-1 flex">
        <div className="flex-1 border-r border-gray-200 dark:border-gray-700">
          <MonacoEditor
            content={editorState.content}
            onChange={handleContentChange}
            onSave={handleSave}
            language="markdown"
          />
        </div>

        <div className="flex-1 overflow-auto">
          <MarkdownPreview content={editorState.content} />
        </div>
      </div>
    </div>
  );
}
