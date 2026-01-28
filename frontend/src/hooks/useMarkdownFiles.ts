import { useState, useEffect, useCallback } from 'react';
import { markdownApi } from '../services/api';
import { MarkdownFile, MarkdownContent, EditorState } from '../types';

export function useMarkdownFiles() {
  const [files, setFiles] = useState<MarkdownFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [editorState, setEditorState] = useState<EditorState>({
    currentFile: null,
    content: '',
    isModified: false,
    isSaving: false,
    lastSaved: null,
    error: null,
  });

  const loadFiles = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await markdownApi.getFiles();
      setFiles(response.files);
    } catch (err) {
      setError('加载文件列表失败');
      console.error('加载文件列表失败:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadFile = useCallback(async (filePath: string) => {
    try {
      setLoading(true);
      setEditorState(prev => ({ ...prev, error: null }));
      const content = await markdownApi.getFile(filePath);
      setEditorState({
        currentFile: content,
        content: content.content,
        isModified: false,
        isSaving: false,
        lastSaved: null,
        error: null,
      });
    } catch (err) {
      const errorMsg = '加载文件失败';
      setEditorState(prev => ({ ...prev, error: errorMsg }));
      console.error('加载文件失败:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const saveFile = useCallback(async () => {
    if (!editorState.currentFile) return;

    try {
      setEditorState(prev => ({ ...prev, isSaving: true, error: null }));
      await markdownApi.saveFile(editorState.currentFile.path, editorState.content);
      setEditorState(prev => ({
        ...prev,
        isModified: false,
        isSaving: false,
        lastSaved: new Date(),
      }));
    } catch (err) {
      const errorMsg = '保存文件失败';
      setEditorState(prev => ({ ...prev, isSaving: false, error: errorMsg }));
      console.error('保存文件失败:', err);
    }
  }, [editorState.content, editorState.currentFile]);

  const updateContent = useCallback((newContent: string) => {
    setEditorState(prev => ({
      ...prev,
      content: newContent,
      isModified: newContent !== (prev.currentFile?.content || ''),
    }));
  }, []);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  return {
    files,
    loading,
    error,
    editorState,
    loadFiles,
    loadFile,
    saveFile,
    updateContent,
  };
}
