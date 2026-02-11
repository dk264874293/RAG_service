/*
 * @Author: 汪培良 rick_wang@yunquna.com
 * @Date: 2026-01-29 18:34:53
 * @LastEditors: 汪培良 rick_wang@yunquna.com
 * @LastEditTime: 2026-02-10 14:20:14
 * @FilePath: /RAG_service/frontend/src/pages/EditorPage.tsx
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
import { Save } from 'lucide-react';
import { useMarkdownFiles } from '../hooks/useMarkdownFiles';
import MonacoEditor from '../components/MonacoEditor';
import MarkdownPreview from '../components/MarkdownPreview';
import FileList from '../components/FileList';

export default function EditorPage() {
    const {
    files,
    loading,
    editorState,
    loadFile,
    saveFile,
    updateContent,
  } = useMarkdownFiles();

  const handleFileSelect = async (file: any) => {
    await loadFile(file.path);
  };

  const handleSave = async () => {
    await saveFile();
  };

  const handleContentChange = (value: string | undefined) => {
    if (value !== undefined) {
      updateContent(value);
    }
  };

  return (
    <div className="flex h-screen">
        <div className="w-64 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
          <FileList
            files={files}
            currentFile={editorState.currentFile}
            onFileSelect={handleFileSelect}
            loading={loading}
          />
        </div>

        <div className="flex-1 flex">
          <div className="flex-1 border-r border-gray-200 dark:border-gray-700 relative">
            <div className="absolute top-2 right-2 z-10">
              <button
                onClick={handleSave}
                disabled={editorState.isSaving || !editorState.currentFile}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <Save size={16} />
                <span className="text-sm">保存</span>
              </button>
            </div>
            <MonacoEditor
              value={editorState.content}
              onChange={handleContentChange}
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
