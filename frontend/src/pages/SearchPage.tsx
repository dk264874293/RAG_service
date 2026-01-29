import React, { useState } from 'react';
import { Search, Zap, BarChart3, FileText, Clock, TrendingUp } from 'lucide-react';
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
        <div className="mb-4 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg p-4">
          <h3 className="font-semibold text-indigo-900 dark:text-indigo-100 mb-2">
            查询扩展信息
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium">原始查询:</span>
              <span className="text-gray-700 dark:text-gray-300">{expanded.query_info.original}</span>
            </div>
            {expanded.expansion_used && (
              <>
                <div className="flex items-center gap-2">
                  <span className="font-medium">重写查询:</span>
                  <span className="text-gray-700 dark:text-gray-300">{expanded.query_info.rewritten}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">扩展变体:</span>
                  <div className="flex flex-wrap gap-2">
                    {expanded.query_info.variants.map((variant, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-indigo-100 dark:bg-indigo-800 text-indigo-800 dark:text-indigo-200 rounded text-xs"
                      >
                        {variant}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">扩展数量:</span>
                  <span className="text-gray-700 dark:text-gray-300">{expanded.query_info.expanded_count}</span>
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
        <div className="mb-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <h3 className="font-semibold text-green-900 dark:text-green-100 mb-2">
            重排序信息
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium">重排序状态:</span>
              <span className={`px-2 py-1 rounded text-xs ${
                reranked.reranking_used
                  ? 'bg-green-100 dark:bg-green-800 text-green-800 dark:text-green-200'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200'
              }`}>
                {reranked.reranking_used ? '已启用' : '未启用'}
              </span>
            </div>
            {reranked.reranking_used && (
              <div className="flex items-center gap-2">
                <span className="font-medium">重排序分数:</span>
                <span className="text-gray-700 dark:text-gray-300">
                  {reranked.reranking_scores.map((score, idx) => (
                    <span key={idx} className="inline-block mr-2">
                      #{idx + 1}: {score.toFixed(4)}
                    </span>
                  ))}
                </span>
              </div>
            )}
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          RAG 智能检索
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          使用向量检索、查询扩展和重排序技术获取最相关的文档内容
        </p>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            搜索模式
          </label>
          <div className="flex gap-3">
            <button
              onClick={() => setSearchMode('basic')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg transition ${
                searchMode === 'basic'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
              }`}
            >
              <Search className="w-4 h-4" />
              <span>基础搜索</span>
            </button>
            <button
              onClick={() => setSearchMode('expanded')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg transition ${
                searchMode === 'expanded'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
              }`}
            >
              <Zap className="w-4 h-4" />
              <span>扩展搜索</span>
            </button>
            <button
              onClick={() => setSearchMode('reranked')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg transition ${
                searchMode === 'reranked'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>重排序搜索</span>
            </button>
          </div>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            返回结果数量: {k}
          </label>
          <input
            type="range"
            min="1"
            max="20"
            value={k}
            onChange={(e) => setK(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            搜索查询
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的问题或搜索内容..."
            rows={3}
            className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
          />
        </div>

        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="mt-4 w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              搜索结果
            </h2>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              找到 {results.total} 个相关文档
            </span>
          </div>

          <div className="space-y-4">
            {results.results.map((result: SearchResult, idx: number) => (
              <div
                key={result.doc_id}
                className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:border-indigo-300 dark:hover:border-indigo-600 transition"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0">
                    <FileText className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                        #{idx + 1}
                      </span>
                      {result.score !== undefined && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          相似度: {(1 - result.score).toFixed(4)}
                        </span>
                      )}
                    </div>
                    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
                      {result.content}
                    </p>
                    {result.metadata && Object.keys(result.metadata).length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                        <details className="text-xs">
                          <summary className="cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100">
                            元数据
                          </summary>
                          <div className="mt-2 space-y-1">
                            {Object.entries(result.metadata).map(([key, value]) => (
                              <div key={key} className="flex items-center gap-2">
                                <span className="font-medium text-gray-700 dark:text-gray-300">
                                  {key}:
                                </span>
                                <span className="text-gray-600 dark:text-gray-400">
                                  {String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
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
