export type SystemFile = { name: string; file_name: string; file_url: string; file_size: number; creation: string }
export type PickableDocument = { doctype: string; docname: string }

export type PickerSource = "all" | "files" | "documents" | "upload"

export type PickerItem =
    | { kind: "upload"; id: "upload" }
    | { kind: "file"; id: string; file: SystemFile }
    | { kind: "document"; id: string; document: PickableDocument }

export type PickerView = "list" | "cards" | "large"
