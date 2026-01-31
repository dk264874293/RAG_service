import { useState, useEffect } from 'react';
import {
  Database,
  RefreshCw,
  BarChart3,
  Activity,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  ArrowUp,
  ArrowDown,
  Info,
  Upload,
  FileText,
  Search,
  Loader2,
  X
} from 'lucide-react';
import { documentService } from '../services/documents';
import { IndexStats, UploadedFile } from '../types';

export default function VectorManagePage() {
  const [stats, setStats] = useState<IndexStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showFiles, setShowFiles] = useState(false);

  const loadStats = async () => {
    try {
      console.log('[VectorManagePage] 开始加载向量统计信息...');
      const data = await documentService.getIndexStats();
      console.log('[VectorManagePage] 加载成功:', data);
      setStats(data);
      setMessage({ type: 'success', text: '向量统计信息已更新' });
      setTimeout(() => setMessage(null), 3000);
    } catch (err: any) {
      console.error('[VectorManagePage] 加载失败:', err);
      console.error('[VectorManagePage] 错误详情:', {
        message: err?.message,
        response: err?.response?.data,
        status: err?.response?.status,
      });
      const errorMsg = err?.response?.data?.message || err?.message || '加载向量统计信息失败，请检查API服务是否正常运行';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadFiles = async () => {
    try {
      const data = await documentService.getUploadHistory(50);
      setFiles(data.items);
    } catch (err: any) {
      console.error('Failed to load files:', err);
    }
  };

  useEffect(() => {
    loadStats();
    loadFiles();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadStats();
    loadFiles();
  };

  const calculateUsagePercentage = () => {
    if (!stats || stats.total_vectors === 0) return 0;
    return ((stats.active_vectors / stats.total_vectors) * 100).toFixed(1);
  };

  const calculateDeletedPercentage = () => {
    if (!stats || stats.total_vectors === 0) return 0;
    return ((stats.deleted_vectors / stats.total_vectors) * 100).toFixed(1);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(e.target.files);
    }
  };

  const handleUpload = async () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      setMessage({ type: 'error', text: '请选择文件' });
      return;
    }

    setUploading(true);
    setMessage(null);

    try {
      const fileArray = Array.from(selectedFiles);
      if (fileArray.length === 1) {
        await documentService.uploadFile(fileArray[0]);
        setMessage({ type: 'success', text: '文件上传成功，向量索引中...' });
      } else {
        const result = await documentService.uploadBatch(fileArray);
        setMessage({ type: 'success', text: `批量上传完成: 成功 ${result.success} 个，失败 ${result.failed} 个` });
      }

      setSelectedFiles(null);
      const fileInput = document.getElementById('vector-file-upload') as HTMLInputElement;
      if (fileInput) fileInput.value = '';

      await loadFiles();
      setTimeout(() => loadStats(), 2000);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || '文件上传失败';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setUploading(false);
      setTimeout(() => {
        if (message?.type === 'success') setMessage(null);
      }, 5000);
    }
  };

  const handleDelete = async (fileId: string, fileName: string) => {
    if (!confirm(`确定要删除文件 "${fileName}" 吗？\n\n删除后，该文件的所有向量也将被移除。`)) {
      return;
    }

    try {
      const response = await documentService.deleteFile(fileId);
      const deletedCount = response.deleted_vectors || 0;
      setMessage({ type: 'success', text: `文件 "${fileName}" 已删除（移除 ${deletedCount} 个向量）` });
      await loadFiles();
      setTimeout(() => loadStats(), 1000);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || '删除文件失败';
      setMessage({ type: 'error', text: errorMsg });
    }
    setTimeout(() => setMessage(null), 5000);
  };

  const filteredFiles = files.filter(file =>
    file.file_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <X className="w-4 h-4 text-red-500" />;
      default:
        return <Loader2 className="w-4 h-4 text-yellow-500 animate-spin" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const metrics = [
    {
      title: '总向量数',
      value: stats?.total_vectors || 0,
      icon: Database,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
      borderColor: 'border-blue-200 dark:border-blue-800',
      trend: null,
      description: 'FAISS索引中的向量总数',
    },
    {
      title: '活跃向量',
      value: stats?.active_vectors || 0,
      icon: Activity,
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-50 dark:bg-green-900/20',
      borderColor: 'border-green-200 dark:border-green-800',
      trend: 'up',
      description: '可用于检索的向量数量',
    },
    {
      title: '已删除向量',
      value: stats?.deleted_vectors || 0,
      icon: Trash2,
      color: 'text-red-600 dark:text-red-400',
      bgColor: 'bg-red-50 dark:bg-red-900/20',
      borderColor: 'border-red-200 dark:border-red-800',
      trend: 'down',
      description: '标记为删除的向量数量',
    },
    {
      title: '向量维度',
      value: stats?.dimension || 0,
      icon: BarChart3,
      color: 'text-purple-600 dark:text-purple-400',
      bgColor: 'bg-purple-50 dark:bg-purple-900/20',
      borderColor: 'border-purple-200 dark:border-purple-800',
      trend: null,
      description: '嵌入向量的维度大小',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-indigo-600 dark:text-indigo-400 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">加载中...</p>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center min-h-screen p-6">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-16 h-16 text-orange-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            无法加载数据
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            向量统计信息无法加载，请检查API服务是否正常运行，或点击刷新按钮重试。
          </p>
          <button
            onClick={loadStats}
            disabled={refreshing}
            className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed mx-auto"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            重新加载
          </button>
          {message && (
            <div className={`mt-4 p-4 rounded-lg ${
              message.type === 'error' ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800' :
              'bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800'
            }`}>
              <p className="text-sm text-gray-800 dark:text-gray-200">
                {message.text}
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 animate-fade-in">
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
              向量管理
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-lg">
              FAISS向量数据库管理和监控
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>

        {message && (
          <div className={`p-4 rounded-lg mb-6 animate-fade-in ${
            message.type === 'success' ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' :
            message.type === 'error' ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800' :
            'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
          }`}>
            <div className="flex items-center gap-3">
              {message.type === 'success' && <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />}
              {message.type === 'error' && <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />}
              {message.type === 'info' && <Info className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
              <p className={`text-sm ${
                message.type === 'success' ? 'text-green-800 dark:text-green-200' :
                message.type === 'error' ? 'text-red-800 dark:text-red-200' :
                'text-blue-800 dark:text-blue-200'
              }`}>
                {message.text}
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metrics.map((metric, idx) => {
          const Icon = metric.icon;
          return (
            <div
              key={idx}
              className={`${metric.bgColor} ${metric.borderColor} border rounded-xl shadow-md p-6 hover:shadow-lg transition-all duration-300 hover:-translate-y-1`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-xl ${metric.color} ${metric.bgColor}`}>
                  <Icon className="w-6 h-6" />
                </div>
                {metric.trend === 'up' && <ArrowUp className="w-5 h-5 text-green-600 dark:text-green-400" />}
                {metric.trend === 'down' && <ArrowDown className="w-5 h-5 text-red-600 dark:text-red-400" />}
              </div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
                {metric.title}
              </p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                {metric.value.toLocaleString()}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-500">
                {metric.description}
              </p>
            </div>
          );
        }        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
            <Database className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            索引使用情况
          </h2>
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">活跃向量占比</span>
                <span className="text-sm font-bold text-green-600 dark:text-green-400">
                  {calculateUsagePercentage()}%
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-green-500 to-green-600 h-full rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${calculateUsagePercentage()}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">已删除向量占比</span>
                <span className="text-sm font-bold text-red-600 dark:text-red-400">
                  {calculateDeletedPercentage()}%
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-red-500 to-red-600 h-full rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${calculateDeletedPercentage()}%` }}
                />
              </div>
            </div>

            {stats && stats.deleted_vectors > 0 && (
              <div className="mt-6 p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-orange-600 dark:text-orange-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-orange-800 dark:text-orange-200 mb-1">
                      性能优化建议
                    </p>
                    <p className="text-xs text-orange-700 dark:text-orange-300">
                      当前有 {stats.deleted_vectors} 个向量已标记为删除，建议定期重建索引以释放存储空间并提高查询性能。
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
            <Info className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            系统信息
          </h2>
          <div className="space-y-4">
            <div className="pb-4 border-b border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">索引路径</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white break-all">
                {stats?.index_path || 'N/A'}
              </p>
            </div>

            <div className="pb-4 border-b border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">向量维度</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {stats?.dimension || 0} 维
              </p>
            </div>

            <div className="pb-4 border-b border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">距离度量</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                L2 (欧几里得距离)
              </p>
            </div>

            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">索引类型</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                FAISS IndexFlatL2
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
          <Upload className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
          上传文档到向量库
        </h2>

        <div className="mb-4">
          <label className="label text-base font-medium">
            选择文件（支持 PDF、Word、TXT、Markdown）
          </label>
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
            <div className="flex-1 w-full md:w-auto">
              <input
                id="vector-file-upload"
                type="file"
                multiple
                onChange={handleFileSelect}
                className="w-full text-sm text-gray-500 dark:text-gray-400
                  file:mr-4 file:py-2.5 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-medium
                  file:bg-indigo-50 file:text-indigo-700
                  hover:file:bg-indigo-100
                  dark:file:bg-gray-700 dark:file:text-indigo-300
                  transition-all duration-200"
              />
            </div>

            <div className="flex gap-3 w-full md:w-auto">
              <button
                onClick={handleUpload}
                disabled={!selectedFiles || uploading}
                className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-medium py-2.5 px-6 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>上传中...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    <span>上传文件</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {selectedFiles && selectedFiles.length > 0 && (
          <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg text-sm text-indigo-800 dark:text-indigo-200">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              <span className="font-medium">已选择 {selectedFiles.length} 个文件</span>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <FileText className="w-6 h-6 text-green-600 dark:text-green-400" />
              已索引文档列表
            </h2>
            <span className="text-sm text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-full">
              共 {files.length} 个文件
            </span>
          </div>
          <button
            onClick={() => setShowFiles(!showFiles)}
            className="flex items-center gap-2 text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 transition-colors"
          >
            {showFiles ? '收起' : '展开'}
          </button>
        </div>

        {showFiles && (
          <>
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="搜索已索引的文件..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200"
              />
            </div>

            <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      状态
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      文件名
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      类型
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      大小
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      上传时间
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredFiles.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                        <div className="flex flex-col items-center justify-center gap-3">
                          <FileText className="h-12 w-12 opacity-30" />
                          <p className="text-lg">暂无已索引的文件</p>
                          <p className="text-sm">上传文件开始使用</p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredFiles.map((file) => (
                      <tr key={file.file_id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-150">
                        <td className="px-6 py-4 whitespace-nowrap">
                          {getStatusIcon(file.processing_status)}
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {file.file_name}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400 font-mono text-xs mt-1">
                            {file.file_id.slice(0, 8)}...
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-3 py-1 inline-flex text-xs font-semibold rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-200">
                            {file.file_type || '未知'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {formatFileSize(file.file_size)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {new Date(file.uploaded_at).toLocaleString('zh-CN')}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right">
                          <button
                            onClick={() => handleDelete(file.file_id, file.file_name)}
                            className="p-2 text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all duration-200"
                            title="删除文件及向量"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
          <Info className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          向量管理说明
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="flex items-start gap-4 p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-200">
            <div className="bg-blue-100 dark:bg-blue-900/30 p-3 rounded-xl flex-shrink-0">
              <Database className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                向量统计
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                实时查看向量数据库的状态和统计信息，包括总向量数、活跃向量数等。
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-200">
            <div className="bg-green-100 dark:bg-green-900/30 p-3 rounded-xl flex-shrink-0">
              <Activity className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                性能监控
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                监控向量索引的使用情况，及时发现性能瓶颈并进行优化。
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-200">
            <div className="bg-red-100 dark:bg-red-900/30 p-3 rounded-xl flex-shrink-0">
              <Trash2 className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                软删除机制
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                使用软删除机制标记删除向量，避免频繁重建索引影响性能。
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
