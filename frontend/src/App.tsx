import React, { useEffect } from 'react';
import Layout from './components/Layout';
import { useMarkdownFiles } from './hooks/useMarkdownFiles';
import { useDebounce } from './hooks/useDebounce';

function App() {
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

  useEffect(() => {
    if (editorState.isModified && debouncedContent !== editorState.currentFile?.content) {
      handleSave();
    }
  }, [debouncedContent]);

  return (
    <Layout
      files={files}
      currentFile={editorState.currentFile}
      editorState={editorState}
      onFileSelect={handleFileSelect}
      onSave={handleSave}
      onRefresh={handleRefresh}
      onContentChange={handleContentChange}
      loading={loading}
    />
  );
}

export default App;
