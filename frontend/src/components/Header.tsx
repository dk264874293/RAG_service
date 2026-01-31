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
  onRefresh,
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
    <div className="h-[50px] bg-[#323233] border-b border-[#252526] flex items-center px-4 justify-between">
      <div className="flex items-center gap-4">
        <FileText size={20} className="text-[#4ec9b0]" />
        <div className="text-sm text-editor-text">
          {fileName || '未选择文件'}
          {isModified && (
            <span className="ml-2 text-[#cca700]">(未保存)</span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {lastSaved && (
          <span className="text-xs text-editor-textMuted mr-2">
            {formatLastSaved(lastSaved)}
          </span>
        )}

        <button
          onClick={onRefresh}
          className="px-3 py-1.5 bg-[#0e639c] hover:bg-[#1177bb] text-white text-sm font-medium rounded transition-colors flex items-center gap-1.5"
        >
          <RefreshCw size={14} />
          刷新
        </button>

        <button
          onClick={onSave}
          disabled={!isModified || isSaving}
          className={`px-3 py-1.5 text-white text-sm font-medium rounded transition-colors flex items-center gap-1.5 ${
            isModified && !isSaving
              ? 'bg-[#0e639c] hover:bg-[#1177bb]'
              : 'bg-[#3c3c3c] cursor-not-allowed opacity-60'
          }`}
        >
          <Save size={14} />
          {isSaving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  );
}
