import { useState } from 'react';
import { Search, Zap, BarChart3, FileText } from 'lucide-react';
import { retrievalService } from '../services/retrieval';
import { SearchResult, ExpandedSearchResponse, RerankedSearchResponse } from '../types';

type SearchMode = 'basic' | 'expanded' | 'reranked';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('basic');
  const [k, setK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!query.trim()) {
      setError('请输入搜索查询');
      return;
    }

    setLoading(true);
    setError('');
    setResults(null);

    try {
      let response;
      switch (searchMode) {
        case 'expanded':
          response = await retrievalService.searchExpanded(query, k);
          break;
        case 'reranked':
          response = await retrievalService.searchReranked(query, k);
          break;
        default:
          response = await retrievalService.search(query, k);
      }

      setResults(response);
    } catch (err: any) {
      setError(err.response?.data?.detail || '搜索失败');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const renderSearchInfo = () => {
    if (!results) return null;

    if (searchMode === 'expanded') {
      const expanded = results as ExpandedSearchResponse;
      return (
        <div className="mb-4 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 border border-indigo-200 dark:border-indigo-800 rounded-xl p-5 animate-fade-in">
          <h3 className="font-semibold text-indigo-900 dark:text-indigo-100 mb-3 flex items-center gap-2">
            <Zap className="w-5 h-5" />
            查询扩展信息
          </h3>
          <div className="space-y-3 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-700 dark:text-gray-300">原始查询:</span>
              <span className="text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 px-2 py-1 rounded">{expanded.query_info.original}</span>
            </div>
            {expanded.expansion_used && (
              <>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-700 dark:text-gray-300">重写查询:</span>
                  <span className="text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 px-2 py-1 rounded">{expanded.query_info.rewritten}</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-medium text-gray-700 dark:text-gray-300 mt-1">扩展变体:</span>
                  <div className="flex flex-wrap gap-2">
                    {expanded.query_info.variants.map((variant, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-indigo-100 dark:bg-indigo-800 text-indigo-800 dark:text-indigo-200 rounded-full text-xs font-medium"
                      >
                        {variant}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-700 dark:text-gray-300">扩展数量:</span>
                  <span className="text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 px-2 py-1 rounded">{expanded.query_info.expanded_count}</span>
                </div>
              </>
            )}
          </div>
        </div>
      );
    }

    if (searchMode === 'reranked') {
      const reranked = results as RerankedSearchResponse;
      return (
        <div className="mb-4 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border border-green-200 dark:border-green-800 rounded-xl p-5 animate-fade-in">
          <h3 className="font-semibold text-green-900 dark:text-green-100 mb-3 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            重排序信息
          </h3>
          <div className="space-y-3 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-700 dark:text-gray-300">重排序状态:</span>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                reranked.reranking_used
                  ? 'bg-green-100 dark:bg-green-800 text-green-800 dark:text-green-200'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200'
              }`}>
                {reranked.reranking_used ? '已启用' : '未启用'}
              </span>
            </div>
            {reranked.reranking_used && (
              <div className="flex items-start gap-2">
                <span className="font-medium text-gray-700 dark:text-gray-300 mt-1">重排序分数:</span>
                <div className="flex flex-wrap gap-2">
                  {reranked.reranking_scores.map((score, idx) => (
                    <span key={idx} className="inline-block px-2 py-1 bg-white dark:bg-gray-800 rounded text-xs">
                      #{idx + 1}: {score.toFixed(4)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="p-6 animate-fade-in">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
          RAG 智能检索
        </h1>
        <p className="text-gray-600 dark:text-gray-400 text-lg">
          使用向量检索、查询扩展和重排序技术获取最相关的文档内容
        </p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-lg animate-fade-in">
          {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 mb-6 hover:shadow-lg transition-shadow duration-300">
        <div className="mb-6">
          <label className="label text-base font-medium">
            搜索模式
          </label>
          <div className="flex gap-3 mt-2">
            <button
              onClick={() => setSearchMode('basic')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl transition-all duration-200 ${
                searchMode === 'basic'
                  ? 'bg-indigo-600 text-white shadow-lg'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              <Search className="w-5 h-5" />
              <span className="font-medium">基础搜索</span>
            </button>
            <button
              onClick={() => setSearchMode('expanded')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl transition-all duration-200 ${
                searchMode === 'expanded'
                  ? 'bg-indigo-600 text-white shadow-lg'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              <Zap className="w-5 h-5" />
              <span className="font-medium">扩展搜索</span>
            </button>
            <button
              onClick={() => setSearchMode('reranked')}
              className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl transition-all duration-200 ${
                searchMode === 'reranked'
                  ? 'bg-indigo-600 text-white shadow-lg'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              <BarChart3 className="w-5 h-5" />
              <span className="font-medium">重排序搜索</span>
            </button>
          </div>
        </div>

        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label className="label text-base font-medium">
              返回结果数量: <span className="text-indigo-600 dark:text-indigo-400 font-bold text-lg">{k}</span>
            </label>
          </div>
          <input
            type="range"
            min="1"
            max="20"
            value={k}
            onChange={(e) => setK(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
          />
        </div>

        <div>
          <label className="label text-base font-medium">
            搜索查询
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的问题或搜索内容..."
            rows={4}
            className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none transition-all duration-200 text-base"
          />
        </div>

        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="mt-6 w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-medium py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-lg shadow-lg hover:shadow-xl"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              <span>搜索中...</span>
            </>
          ) : (
            <>
              <Search className="w-5 h-5" />
              <span>搜索</span>
            </>
          )}
        </button>
      </div>

      {renderSearchInfo()}

      {results && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow duration-300 animate-fade-in">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              搜索结果
            </h2>
            <span className="text-sm text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-full">
              找到 {results.total} 个相关文档
            </span>
          </div>

          <div className="space-y-4">
            {results.results.map((result: SearchResult, idx: number) => (
              <div
                key={result.doc_id}
                className="border border-gray-200 dark:border-gray-700 rounded-xl p-5 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-md transition-all duration-200 group"
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 mt-1">
                    <div className="bg-indigo-100 dark:bg-indigo-900/30 p-3 rounded-lg group-hover:scale-110 transition-transform duration-200">
                      <FileText className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-1 rounded-full">
                        #{idx + 1}
                      </span>
                      {result.score !== undefined && (
                        <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded-full">
                          相似度: {(1 - result.score).toFixed(4)}
                        </span>
                      )}
                    </div>
                    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
                      {result.content}
                    </p>
                    {result.metadata && Object.keys(result.metadata).length > 0 && (
                      <details className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 group">
                        <summary className="cursor-pointer text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors">
                          元数据
                        </summary>
                        <div className="mt-3 space-y-2 text-sm">
                          {Object.entries(result.metadata).map(([key, value]) => (
                            <div key={key} className="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                              <span className="font-medium text-gray-700 dark:text-gray-300 min-w-[80px]">
                                {key}:
                              </span>
                              <span className="text-gray-600 dark:text-gray-400">
                                {String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
