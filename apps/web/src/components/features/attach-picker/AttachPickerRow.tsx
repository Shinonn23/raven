import { CornerDownLeftIcon, FileBoxIcon, FileIcon, UploadIcon } from "lucide-react"
import { Checkbox } from "@components/ui/checkbox"
import { formatRelativeDate } from "@lib/date"
import { cn } from "@lib/utils"
import _ from "@lib/translate"
import { fileTypeLabel } from "./attachPickerItems"
import type { PickerItem } from "./types"

interface AttachPickerRowProps {
    item: PickerItem
    isActive: boolean
    isChecked: boolean
    onActivate: () => void
    onHover: () => void
}

const rowClassName = (isActive: boolean) =>
    cn("flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-start text-sm text-ink-gray-8", isActive && "bg-surface-gray-3")

const EnterHint = ({ isActive }: { isActive: boolean }) => isActive ? <CornerDownLeftIcon className="size-3.5 text-ink-gray-5" aria-hidden /> : null

/** One row of the picker: the upload action, a system file (checkbox), or a document. */
export const AttachPickerRow = ({ item, isActive, isChecked, onActivate, onHover }: AttachPickerRowProps) => {
    const common = { type: "button" as const, role: "option" as const, "aria-selected": isActive, onClick: onActivate, onMouseMove: onHover }

    if (item.kind === "upload") {
        return (
            <button {...common} className={rowClassName(isActive)}>
                <UploadIcon className="size-4 shrink-0" />
                <span className="flex-1 text-base-medium">{_("Upload from computer")}</span>
                <EnterHint isActive={isActive} />
            </button>
        )
    }
    if (item.kind === "file") {
        return (
            <button {...common} className={rowClassName(isActive)}>
                <Checkbox checked={isChecked} tabIndex={-1} aria-hidden className="pointer-events-none" />
                <span className="min-w-0 truncate text-base-medium">{item.file.file_name}</span>
                <span className="shrink-0 text-xs text-ink-gray-4">· {formatRelativeDate(item.file.creation)}</span>
                <span className="ms-auto flex shrink-0 items-center gap-2 text-xs text-ink-gray-5">
                    <EnterHint isActive={isActive} />{fileTypeLabel(item.file.file_name)}<FileIcon className="size-4 text-ink-blue-3" />
                </span>
            </button>
        )
    }
    return (
        <button {...common} className={rowClassName(isActive)}>
            <FileBoxIcon className="size-4 shrink-0 text-ink-gray-5" />
            <span className="min-w-0 truncate text-base-medium">{item.document.docname}</span>
            <span className="ms-auto flex shrink-0 items-center gap-2 text-xs text-ink-gray-5">
                <EnterHint isActive={isActive} />{item.document.doctype}
            </span>
        </button>
    )
}
