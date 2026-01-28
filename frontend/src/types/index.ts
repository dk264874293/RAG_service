export interface MarkdownFile {
  name: string;
  path: string;
  folder_name: string;
  url: string;
  size: number;
  modified_time: string;
}

export interface MarkdownFileList {
  files: MarkdownFile[];
}

export interface MarkdownContent {
  content: string;
  path: string;
  name: string;
  folder_name: string;
}

export interface MarkdownSaveRequest {
  content: string;
}

export interface MarkdownSaveResponse {
  status: string;
  message: string;
  path: string;
}

export interface EditorState {
  currentFile: MarkdownContent | null;
  content: string;
  isModified: boolean;
  isSaving: boolean;
  lastSaved: Date | null;
  error: string | null;
}
