import { FileIcon, XIcon } from "lucide-react"
import { Button } from "@components/ui/button"
import { fileTypeLabel, isImageFile } from "../attach-picker/attachPickerItems"
import { cn } from "@lib/utils"
import _ from "@lib/translate"
import type { ChatbotAttachment } from "./types"

interface ChatbotAttachmentCardProps {
    file: ChatbotAttachment
    /** Set while staged in the composer: shows the remove button. Omit for sent messages, where the card opens the file. */
    onRemove?: () => void
    className?: string
}

/** An attached file as a card: a thumbnail for images, an icon with the type for everything else. */
export const ChatbotAttachmentCard = ({ file, onRemove, className }: ChatbotAttachmentCardProps) => {
    const isImage = isImageFile(file.file_name)
    const card = (
        <div className={cn("flex flex-col overflow-clip rounded-lg border border-outline-gray-2 bg-surface-base", className)}>
            <div className="flex flex-1 items-center justify-center bg-surface-gray-2">
                {isImage
                    ? <img src={file.file_url} alt={file.file_name} loading="lazy" className="size-full object-cover" />
                    : <div className="flex flex-col items-center gap-1 p-3"><FileIcon className="size-7 text-ink-gray-5" /><span className="text-xs text-ink-gray-5">{fileTypeLabel(file.file_name)}</span></div>}
            </div>
            <span className="truncate px-2 py-1 text-xs text-ink-gray-7">{file.file_name}</span>
        </div>
    )

    if (!onRemove) return <a href={file.file_url} target="_blank" rel="noreferrer" className="block">{card}</a>
    return (
        <div className="relative">
            {card}
            <Button type="button" variant="subtle" size="sm" isIconButton aria-label={_("Remove file")} className="absolute end-1 top-1 size-5 rounded-full" onClick={onRemove}>
                <XIcon className="size-3" />
            </Button>
        </div>
    )
}
