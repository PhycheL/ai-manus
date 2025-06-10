// Backend API service
import { apiClient, BASE_URL, ApiResponse } from './client';
import { fetchEventSource, EventSourceMessage } from '@microsoft/fetch-event-source';
import { AgentSSEEvent } from '../types/event';
import { CreateSessionResponse, GetSessionResponse, ShellViewResponse, FileViewResponse, ListSessionResponse } from '../types/response';

/**
 * Create Session
 * @returns Session
 */
export async function createSession(): Promise<CreateSessionResponse> {
  const response = await apiClient.put<ApiResponse<CreateSessionResponse>>('/sessions');
  return response.data.data;
}

export async function getSession(sessionId: string): Promise<GetSessionResponse> {
  const response = await apiClient.get<ApiResponse<GetSessionResponse>>(`/sessions/${sessionId}`);
  return response.data.data;
}

export async function getSessions(): Promise<ListSessionResponse> {
  const response = await apiClient.get<ApiResponse<ListSessionResponse>>('/sessions');
  return response.data.data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete<ApiResponse<void>>(`/sessions/${sessionId}`);
}

export async function stopSession(sessionId: string): Promise<void> {
  await apiClient.post<ApiResponse<void>>(`/sessions/${sessionId}/stop`);
}

export const getVNCUrl = (sessionId: string): string => {
  // Convert http to ws, https to wss
  const wsBaseUrl = BASE_URL.replace(/^http/, 'ws');
  return `${wsBaseUrl}/sessions/${sessionId}/vnc`;
}

interface ChatCallbacks {
  onOpen: () => void;
  onMessage: (event: AgentSSEEvent) => void;
  onClose: () => void;
  onError?: (error: Error) => void;
}

/**
 * Chat with Session (using SSE to receive streaming responses)
 * @returns A function to cancel the SSE connection
 */
export const chatWithSession = async (
  sessionId: string, 
  message: string = '',
  eventId?: string,
  callbacks?: ChatCallbacks
): Promise<() => void> => {
  const { onOpen, onMessage, onClose, onError } = callbacks || {};
  
  // Create AbortController for cancellation
  const abortController = new AbortController();
  
  try {
    const apiUrl = `${BASE_URL}/sessions/${sessionId}/chat`;
    
    // Start the SSE connection (this is async but we don't await it)
    const ssePromise = fetchEventSource(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      openWhenHidden: true,
      body: JSON.stringify({ message, timestamp: Math.floor(Date.now() / 1000), event_id: eventId }),
      signal: abortController.signal,
      async onopen() {
        if (onOpen) {
          onOpen();
        }
      },
      onmessage(event: EventSourceMessage) {
        if (event.event && event.event.trim() !== '') {
          if (onMessage) {
          onMessage({
              event: event.event as AgentSSEEvent['event'],
              data: JSON.parse(event.data) as AgentSSEEvent['data']
            });
          }
        }
      },
      onclose() {
        if (onClose) {
          onClose();
        }
      },
      onerror(err: any) {
        console.error('EventSource error:', err);
        if (onError) {
          onError(err instanceof Error ? err : new Error(String(err)));
        }
        throw err;
      },
    });

    // Handle the SSE promise in the background
    ssePromise.catch((error) => {
      // Only handle errors that are not due to abortion
      if (!abortController.signal.aborted) {
        console.error('Chat error:', error);
        if (onError) {
          onError(error instanceof Error ? error : new Error(String(error)));
        }
      }
    });

    // Return the cancel function immediately
    return () => {
      abortController.abort();
    };
  } catch (error) {
    console.error('Chat setup error:', error);
    if (onError) {
      onError(error instanceof Error ? error : new Error(String(error)));
    }
    // Return a no-op cancel function
    return () => {};
  }
};

/**
 * View Shell session output
 * @param sessionId Session ID
 * @param shellSessionId Shell session ID
 * @returns Shell session output content
 */
export async function viewShellSession(sessionId: string, shellSessionId: string): Promise<ShellViewResponse> {
  const response = await apiClient.post<ApiResponse<ShellViewResponse>>(`/sessions/${sessionId}/shell`, { session_id: shellSessionId });
  return response.data.data;
}

/**
 * View file content
 * @param sessionId Session ID
 * @param file File path
 * @returns File content
 */
export async function viewFile(sessionId: string, file: string): Promise<FileViewResponse> {
  const response = await apiClient.post<ApiResponse<FileViewResponse>>(`/sessions/${sessionId}/file`, { file });
  return response.data.data;
}

// 文件上传相关类型定义
export interface UploadFileResponse {
  file_id: string;
  filename: string;
  original_filename: string;
  size: number;
  path: string;
  mime_type: string;
  session_id: string | null;
}

export interface UploadedFile {
  file_id: string;
  filename: string;
  size: number;
  path: string;
  mime_type: string;
  created_at: number;
}

export interface ListFilesResponse {
  files: UploadedFile[];
}

/**
 * 上传文件到沙盒
 * @param files 要上传的文件数组
 * @returns 上传结果
 */
export async function uploadFiles(files: File[]): Promise<UploadFileResponse[]> {
  const uploadPromises = files.map(async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    // 直接连接到沙盒的上传API
    const response = await fetch('http://localhost:8080/api/v1/files/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`上传文件 ${file.name} 失败: ${response.statusText}`);
    }

    const result = await response.json();
    // 沙盒API返回格式：{ success: boolean, message: string, data: {...} }
    if (result.success) {
      return result.data;
    } else {
      throw new Error(`上传文件 ${file.name} 失败: ${result.message}`);
    }
  });

  return Promise.all(uploadPromises);
}

/**
 * 获取已上传的文件列表
 * @returns 文件列表
 */
export async function getUploadedFiles(): Promise<ListFilesResponse> {
  const response = await fetch('http://localhost:8080/api/v1/files/list');
  
  if (!response.ok) {
    throw new Error(`获取文件列表失败: ${response.statusText}`);
  }

  const result = await response.json();
  // 沙盒API返回格式：{ success: boolean, message: string, data: { files: [...] } }
  if (result.success) {
    return result.data;
  } else {
    throw new Error(`获取文件列表失败: ${result.message}`);
  }
}

/**
 * 删除已上传的文件
 * @param fileId 文件ID
 */
export async function deleteUploadedFile(fileId: string): Promise<void> {
  const response = await fetch(`http://localhost:8080/api/v1/files/${fileId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`删除文件失败: ${response.statusText}`);
  }
}