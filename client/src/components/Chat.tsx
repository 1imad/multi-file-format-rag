import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/tokyo-night-dark.css';
import { IoSend, IoCopy, IoCheckmark, IoMoon, IoSunny, IoSettings } from 'react-icons/io5';
import { MdStop, MdRefresh, MdVisibility } from 'react-icons/md';
import { FiUser } from 'react-icons/fi';
import { RiRobot2Line } from 'react-icons/ri';
import FileList from './FileList';
import UploadModal from './UploadModal';
import HtmlPreviewModal from './HtmlPreviewModal';
import SettingsModal from './SettingsModal';
import type { SettingsData } from './SettingsModal';
import './Chat.css';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatProps {
  apiUrl?: string;
  systemPrompt?: string;
  token: string;
  onLogout: () => void;
}

export default function Chat({ apiUrl = 'http://localhost:8000', systemPrompt = 'default', token, onLogout }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [fileListKey, setFileListKey] = useState(0);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [htmlPreviewContent, setHtmlPreviewContent] = useState('');
  const [isHtmlPreviewOpen, setIsHtmlPreviewOpen] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [copiedResponse, setCopiedResponse] = useState<number | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const savedTheme = localStorage.getItem('chat-theme');
    return (savedTheme as 'light' | 'dark') || 'light';
  });
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<SettingsData>(() => {
    const savedSettings = localStorage.getItem('chat-settings');
    return savedSettings ? JSON.parse(savedSettings) : {
      backendUrl: apiUrl,
      embeddingModel: 'text-embedding-3-small',
      llmModel: 'gpt-4o-mini',
    };
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStreamingMessage]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('chat-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const handleSettingsSave = (newSettings: SettingsData) => {
    setSettings(newSettings);
    localStorage.setItem('chat-settings', JSON.stringify(newSettings));
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    
    // Auto-resize textarea
    e.target.style.height = 'auto';
    const newHeight = Math.min(e.target.scrollHeight, 8 * 24); // 8 rows * 24px line-height
    e.target.style.height = `${newHeight}px`;
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);
    setCurrentStreamingMessage('');
    
    // Reset textarea height
    const textarea = document.querySelector('.chat-input') as HTMLTextAreaElement;
    if (textarea) {
      textarea.style.height = 'auto';
    }

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${settings.backendUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: userMessage.content,
          chat_history: messages,
          system_prompt: systemPrompt,
          embedding_model: settings.embeddingModel,
          llm_model: settings.llmModel,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Token expired or invalid, logout user
          onLogout();
          throw new Error('Session expired. Please login again.');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No reader available');
      }

      let accumulatedContent = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        accumulatedContent += chunk;
        setCurrentStreamingMessage(accumulatedContent);
      }

      // Add the complete message to chat history
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: accumulatedContent,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setCurrentStreamingMessage('');
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Request aborted');
      } else {
        console.error('Error:', error);
        const errorMessage: ChatMessage = {
          role: 'assistant',
          content: `Error: ${error.message}`,
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const stopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleUploadSuccess = () => {
    // Refresh file list when upload succeeds
    setFileListKey(prev => prev + 1);
  };

  const handleHtmlPreview = (htmlCode: string) => {
    setHtmlPreviewContent(htmlCode);
    setIsHtmlPreviewOpen(true);
  };

  const handleCopyCode = async (code: string, codeId: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(codeId);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  const handleCopyResponse = async (content: string, messageIndex: number) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedResponse(messageIndex);
      setTimeout(() => setCopiedResponse(null), 2000);
    } catch (err) {
      console.error('Failed to copy response:', err);
    }
  };

  // Custom code component to add preview button for HTML
  const CodeBlock = ({ inline, className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';
    
    // Extract text content properly from children
    const getTextContent = (node: any): string => {
      if (typeof node === 'string') return node;
      if (Array.isArray(node)) return node.map(getTextContent).join('');
      if (node?.props?.children) return getTextContent(node.props.children);
      return '';
    };
    
    const code = getTextContent(children).replace(/\n$/, '');
    const isHtml = language === 'html' || language === 'htm';
    const codeId = `code-${Math.random().toString(36).substr(2, 9)}`;
    const isCopied = copiedCode === codeId;

    if (!inline && isHtml) {
      return (
        <div className="code-block-container">
          <div className="code-block-header">
            <span className="code-language">{language}</span>
            <div className="code-block-actions">
              <button
                className="btn-copy-code"
                onClick={() => handleCopyCode(code, codeId)}
                title="Copy code"
              >
                {isCopied ? <IoCheckmark /> : <IoCopy />}
                {isCopied ? 'Copied!' : 'Copy'}
              </button>
              <button
                className="btn-preview-html"
                onClick={() => handleHtmlPreview(code)}
                title="Preview HTML"
              >
                <MdVisibility />
                Preview
              </button>
            </div>
          </div>
          <pre className={className}>
            <code className={className} {...props}>
              {children}
            </code>
          </pre>
        </div>
      );
    }

    if (!inline) {
      return (
        <div className="code-block-container">
          <div className="code-block-header">
            <span className="code-language">{language || 'code'}</span>
            <button
              className="btn-copy-code"
              onClick={() => handleCopyCode(code, codeId)}
              title="Copy code"
            >
              {isCopied ? <IoCheckmark /> : <IoCopy />}
              {isCopied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <pre className={className}>
            <code className={className} {...props}>
              {children}
            </code>
          </pre>
        </div>
      );
    }

    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  };

  const handleRegenerate = async () => {
    if (messages.length === 0 || isStreaming) return;

    // Find the last user message
    let lastUserMessageIndex = -1;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        lastUserMessageIndex = i;
        break;
      }
    }

    if (lastUserMessageIndex === -1) return;

    const lastUserMessage = messages[lastUserMessageIndex];
    
    // Remove all messages after the last user message
    const updatedMessages = messages.slice(0, lastUserMessageIndex + 1);
    setMessages(updatedMessages);
    
    setIsStreaming(true);
    setCurrentStreamingMessage('');

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${settings.backendUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: lastUserMessage.content,
          chat_history: updatedMessages.slice(0, -1), // Exclude the last user message from history
          system_prompt: systemPrompt,
          embedding_model: settings.embeddingModel,
          llm_model: settings.llmModel,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No reader available');
      }

      let accumulatedContent = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        accumulatedContent += chunk;
        setCurrentStreamingMessage(accumulatedContent);
      }

      // Add the complete message to chat history
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: accumulatedContent,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setCurrentStreamingMessage('');
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Request aborted');
      } else {
        console.error('Error:', error);
        const errorMessage: ChatMessage = {
          role: 'assistant',
          content: `Error: ${error.message}`,
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="chat-layout">
      <div className="chat-container">
        <div className="chat-header">
        <h2>RAG Chat Assistant</h2>
        <div className="chat-info">
          <span className="prompt-badge">{systemPrompt}</span>
          <button 
            className="btn-theme-toggle" 
            onClick={toggleTheme}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          >
            {theme === 'light' ? <IoMoon /> : <IoSunny />}
          </button>
          <button 
            className="btn-settings" 
            onClick={() => setIsSettingsOpen(true)}
            title="Settings"
          >
            <IoSettings />
          </button>
          <button 
            className="btn-logout" 
            onClick={onLogout}
            title="Logout"
          >
            Logout
          </button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => {
          const isLastMessage = index === messages.length - 1;
          const isLastAssistantMessage = isLastMessage && message.role === 'assistant';
          
          return (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-avatar">
                {message.role === 'user' ? <FiUser /> : <RiRobot2Line />}
              </div>
              <div className="message-content">
                <ReactMarkdown 
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    code: CodeBlock
                  }}
                >
                  {message.content}
                </ReactMarkdown>
                {message.role === 'assistant' && (
                  <div className="message-actions">
                    <button 
                      className="btn-copy-response"
                      onClick={() => handleCopyResponse(message.content, index)}
                      title="Copy response"
                    >
                      {copiedResponse === index ? <IoCheckmark /> : <IoCopy />}
                      {copiedResponse === index ? 'Copied!' : 'Copy'}
                    </button>
                    {isLastAssistantMessage && !isStreaming && (
                      <button 
                        className="btn-regenerate"
                        onClick={handleRegenerate}
                        title="Regenerate response"
                      >
                        <MdRefresh />
                        Regenerate
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {currentStreamingMessage && (
          <div className="message assistant streaming">
            <div className="message-avatar">
              <RiRobot2Line />
            </div>
            <div className="message-content">
              <ReactMarkdown 
                rehypePlugins={[rehypeHighlight]}
                components={{
                  code: CodeBlock
                }}
              >
                {currentStreamingMessage}
              </ReactMarkdown>
              <span className="streaming-indicator">▊</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="input-wrapper">
          <textarea
            className="chat-input"
            value={input}
            onChange={handleInput}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about your documents..."
            disabled={isStreaming}
            rows={1}
          />
          <div className="chat-actions">
            {isStreaming ? (
              <button className="btn btn-stop" onClick={stopStreaming}>
                <MdStop />
              </button>
            ) : (
              <button
                className="btn btn-send"
                onClick={handleSend}
                disabled={!input.trim()}
              >
                <IoSend />
              </button>
            )}
          </div>
        </div>
      </div>
      </div>
      <div className="file-list-panel">
        <FileList 
          key={fileListKey} 
          apiUrl={apiUrl} 
          token={token}
          onFileDeleted={() => setFileListKey(prev => prev + 1)}
          onUploadClick={() => setIsUploadModalOpen(true)}
        />
      </div>
      <UploadModal 
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
        apiUrl={apiUrl}
        token={token}
      />
      <HtmlPreviewModal
        isOpen={isHtmlPreviewOpen}
        onClose={() => setIsHtmlPreviewOpen(false)}
        htmlContent={htmlPreviewContent}
      />
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSave={handleSettingsSave}
        currentSettings={settings}
      />
    </div>
  );
}
