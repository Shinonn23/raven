import { CheckIcon, FileBoxIcon, FileIcon, UploadIcon } from "lucide-react"
import { formatRelativeDate } from "@lib/date"
import { cn } from "@lib/utils"
import _ from "@lib/translate"
import { fileTypeLabel, isImageFile } from "./attachPickerItems"
import type { PickerItem, PickerView } from "./types"

interface AttachPickerCardProps {
    item: PickerItem
    view: Exclude<PickerView, "list">
    isActive: boolean
    isChecked: boolean
    onActivate: () => void
    onHover: () => void
}

const Preview = ({ item, view }: Pick<AttachPickerCardProps, "item" | "view">) => {
    const icon = "size-8 text-ink-gray-5"
    if (item.kind === "upload") return <UploadIcon className={icon} />
    if (item.kind === "document") return <FileBoxIcon className={icon} />
    if (isImageFile(item.file.file_name)) {
        return <img src={item.file.file_url} alt="" loading="lazy" className={cn("size-full object-cover", view === "large" && "object-contain")} />
    }
    return (
        <div className="flex flex-col items-center gap-1">
            <FileIcon className={icon} />
            <span className="text-xs text-ink-gray-5">{fileTypeLabel(item.file.file_name)}</span>
        </div>
    )
}

const captions = (item: PickerItem): [string, string] => {
    if (item.kind === "upload") return [_("Upload from computer"), ""]
    if (item.kind === "document") return [item.document.docname, item.document.doctype]
    return [item.file.file_name, formatRelativeDate(item.file.creation)]
}

/** A tile for the card views: a preview (image thumbnail for images) over a name and a caption. */
export const AttachPickerCard = ({ item, view, isActive, isChecked, onActivate, onHover }: AttachPickerCardProps) => {
    const [title, caption] = captions(item)
    return (
        <button
            type="button"
            role="option"
            aria-selected={isActive}
            onClick={onActivate}
            onMouseMove={onHover}
            className={cn("relative flex min-w-0 shrink-0 flex-col overflow-clip rounded-lg border border-outline-gray-2 text-start", isActive && "bg-surface-gray-3 ring-1 ring-outline-gray-4")}
        >
            <div className={cn("flex w-full shrink-0 items-center justify-center overflow-clip bg-surface-gray-2", view === "large" ? "h-40" : "h-24")}>
                <Preview item={item} view={view} />
            </div>
            {item.kind === "file" && (
                <span className={cn("absolute start-2 top-2 flex size-5 items-center justify-center rounded border bg-surface-base", isChecked ? "border-outline-gray-5 bg-surface-gray-7 text-ink-white" : "border-outline-gray-3")}>
                    {isChecked && <CheckIcon className="size-3.5" />}
                </span>
            )}
            <div className="min-w-0 px-2.5 py-2">
                <div className="truncate text-sm font-medium text-ink-gray-8">{title}</div>
                {caption && <div className="truncate text-xs text-ink-gray-5">{caption}</div>}
            </div>
        </button>
    )
}
