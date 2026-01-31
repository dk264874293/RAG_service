import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Database,
  Search,
  RefreshCw,
  BarChart3,
  Zap,
  Activity,
  Clock,
  TrendingUp
} from 'lucide-react';
import { documentService } from '../services/documents';
import { IndexStats } from '../types';

export default function DashboardPage() {
  const [stats, setStats] = useState<IndexStats | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await documentService.getIndexStats();
      setStats(data);
    } catch (err: any) {
      console.error('Failed to load stats:', err);
      const errorMsg = err?.response?.data?.message || err?.message || '加载统计信息失败';
      console.error('Error details:', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const quickActions = [
    {
      title: '上传文档',
      description: '添加新的文档到RAG系统',
      icon: FileText,
      action: () => navigate('/documents'),
      color: 'from-indigo-500 to-indigo-600',
      bgColor: 'bg-indigo-500',
    },
    {
      title: '智能检索',
      description: '使用RAG进行语义搜索',
      icon: Search,
      action: () => navigate('/search'),
      color: 'from-green-500 to-green-600',
      bgColor: 'bg-green-500',
    },
    {
      title: '文档管理',
      description: '查看和管理已上传的文档',
      icon: Database,
      action: () => navigate('/documents'),
      color: 'from-blue-500 to-blue-600',
      bgColor: 'bg-blue-500',
    },
  ];

  const metricCards = [
    {
      title: '总向量数',
      value: stats?.total_vectors || 0,
      icon: Database,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
      borderColor: 'border-blue-200 dark:border-blue-800',
      description: 'FAISS索引中的向量总数',
    },
    {
      title: '活跃向量',
      value: stats?.active_vectors || 0,
      icon: Activity,
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-50 dark:bg-green-900/20',
      borderColor: 'border-green-200 dark:border-green-800',
      description: '可用于检索的向量数量',
    },
    {
      title: '已删除向量',
      value: stats?.deleted_vectors || 0,
      icon: Zap,
      color: 'text-orange-600 dark:text-orange-400',
      bgColor: 'bg-orange-50 dark:bg-orange-900/20',
      borderColor: 'border-orange-200 dark:border-orange-800',
      description: '标记为删除的向量数量',
    },
    {
      title: '向量维度',
      value: stats?.dimension || 0,
      icon: BarChart3,
      color: 'text-purple-600 dark:text-purple-400',
      bgColor: 'bg-purple-50 dark:bg-purple-900/20',
      borderColor: 'border-purple-200 dark:border-purple-800',
      description: '嵌入向量的维度大小',
    },
  ];

  return (
    <div className="p-6 animate-fade-in">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
          控制台
        </h1>
        <p className="text-gray-600 dark:text-gray-400 text-lg">
          RAG系统性能监控和快速操作
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metricCards.map((metric, idx) => (
          <div
            key={idx}
            className={`${metric.bgColor} ${metric.borderColor} border rounded-xl shadow-md p-6 hover:shadow-lg transition-all duration-300 hover:-translate-y-1`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {metric.title}
                </p>
                <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                  {metric.value.toLocaleString()}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                  {metric.description}
                </p>
              </div>
              <div className={`p-3 rounded-xl ${metric.color} ${metric.bgColor}`}>
                <metric.icon className="w-8 h-8" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                快速操作
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {quickActions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={action.action}
                  className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl hover:border-indigo-500 dark:hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-all duration-300 group hover:-translate-y-1"
                >
                  <div className={`bg-gradient-to-br ${action.color} p-4 rounded-full mb-4 group-hover:scale-110 transition-transform duration-300 shadow-lg`}>
                    <action.icon className="w-7 h-7 text-white" />
                  </div>
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                    {action.title}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
                    {action.description}
                  </p>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                系统信息
              </h2>
              <button
                onClick={loadStats}
                disabled={loading}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors duration-200"
              >
                <RefreshCw className={`w-5 h-5 text-gray-600 dark:text-gray-400 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-3 pb-4 border-b border-gray-200 dark:border-gray-700">
                <Database className="w-5 h-5 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-600 dark:text-gray-400">索引路径</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {stats?.index_path || 'N/A'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 pb-4 border-b border-gray-200 dark:border-gray-700">
                <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-600 dark:text-gray-400">活跃率</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {stats && stats.total_vectors > 0
                      ? `${((stats.active_vectors / stats.total_vectors) * 100).toFixed(1)}%`
                      : 'N/A'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-600 dark:text-gray-400">最后更新</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {new Date().toLocaleTimeString('zh-CN')}
                  </p>
                </div>
              </div>
            </div>

            {stats && stats.deleted_vectors > 0 && (
              <div className="mt-4 p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg animate-fade-in">
                <p className="text-sm text-orange-800 dark:text-orange-200">
                  ⚠️ 有 {stats.deleted_vectors} 个向量已标记为删除，建议定期重建索引以优化性能。
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          系统功能说明
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="flex items-start gap-4 p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-200">
            <div className="bg-indigo-100 dark:bg-indigo-900/30 p-3 rounded-xl flex-shrink-0">
              <Search className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                语义检索
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                基于FAISS向量数据库的高效语义相似度搜索
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-200">
            <div className="bg-green-100 dark:bg-green-900/30 p-3 rounded-xl flex-shrink-0">
              <Zap className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                查询扩展
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                使用同义词和查询重写提高检索召回率
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-200">
            <div className="bg-purple-100 dark:bg-purple-900/30 p-3 rounded-xl flex-shrink-0">
              <BarChart3 className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                结果重排序
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                使用交叉编码器模型提升结果排序准确性
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
