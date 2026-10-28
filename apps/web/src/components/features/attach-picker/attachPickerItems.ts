import type { PickableDocument, PickerItem, PickerSource, PickerView, SystemFile } from "./types"

export const sourcesFor = (hasDocuments: boolean): PickerSource[] =>
    hasDocuments ? ["all", "files", "documents", "upload"] : ["all", "files", "upload"]

/** Wraps around, so ← on the first source lands on the last. */
export const stepSource = (sources: PickerSource[], current: PickerSource, step: 1 | -1): PickerSource =>
    sources[(sources.indexOf(current) + step + sources.length) % sources.length]

const matches = (search: string, ...texts: string[]) =>
    texts.some((text) => text.toLowerCase().includes(search.trim().toLowerCase()))

/** The navigable rows for a source: the upload action, system files, and frequently used documents. */
export const buildItems = (source: PickerSource, files: SystemFile[], documents: PickableDocument[], search: string): PickerItem[] => {
    const items: PickerItem[] = []
    if (source === "all" || source === "upload") items.push({ kind: "upload", id: "upload" })
    if (source === "all" || source === "files") items.push(...files.map((file): PickerItem => ({ kind: "file", id: file.file_url, file })))
    if (source === "all" || source === "documents") {
        items.push(...documents
            .filter((document) => matches(search, document.docname, document.doctype))
            .map((document): PickerItem => ({ kind: "document", id: `${document.doctype}/${document.docname}`, document })))
    }
    return items
}

export const fileTypeLabel = (fileName: string) => fileName.includes(".") ? fileName.split(".").pop()!.toUpperCase() : "FILE"

const IMAGE_EXTENSIONS = new Set(["png", "jpg", "jpeg", "gif", "webp", "svg", "avif"])

export const isImageFile = (fileName: string) => IMAGE_EXTENSIONS.has(fileName.split(".").pop()?.toLowerCase() ?? "")

/** Items per row in each view; ↑ / ↓ move by this much. */
export const COLUMNS: Record<PickerView, number> = { list: 1, cards: 3, large: 2 }

/** The next active index after ↑ / ↓: one row up or down, staying on the same item at the edges. */
export const stepIndex = (index: number, direction: 1 | -1, columns: number, length: number) => {
    const next = index + direction * columns
    return next < 0 || next >= length ? index : next
}
