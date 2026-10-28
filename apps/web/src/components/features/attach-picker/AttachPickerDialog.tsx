import { useRef, useState, type KeyboardEvent } from "react"
import { ArrowDownIcon, ArrowLeftIcon, ArrowRightIcon, ArrowUpIcon, CornerDownLeftIcon, LayoutGridIcon, ListIcon, SearchIcon, RectangleHorizontalIcon } from "lucide-react"
import { Button } from "@components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@components/ui/dialog"
import { Kbd } from "@components/ui/kbd"
import { Skeleton } from "@components/ui/skeleton"
import { cn } from "@lib/utils"
import _ from "@lib/translate"
import { AttachPickerCard } from "./AttachPickerCard"
import { AttachPickerRow } from "./AttachPickerRow"
import { buildItems, COLUMNS, sourcesFor, stepIndex, stepSource } from "./attachPickerItems"
import { useAttachPickerView } from "./useAttachPickerView"
import { useAttachableFiles } from "./useAttachableFiles"
import type { PickableDocument, PickerItem, PickerSource, PickerView, SystemFile } from "./types"

export interface AttachPickerDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    /** Opens the browser's file chooser; the host receives the chosen files. */
    onUploadFiles: (files: File[]) => void
    onPickSystemFiles: (files: SystemFile[]) => void
    /** Frequently used documents. Provide with `onPickDocument` to show the Documents source. */
    documents?: PickableDocument[]
    onPickDocument?: (document: PickableDocument) => void
}

const SOURCE_LABELS: Record<PickerSource, () => string> = {
    all: () => _("All"),
    files: () => _("Files"),
    documents: () => _("Documents"),
    upload: () => _("Upload"),
}

const VIEW_OPTIONS: { view: PickerView; label: () => string; Icon: typeof ListIcon }[] = [
    { view: "list", label: () => _("List"), Icon: ListIcon },
    { view: "cards", label: () => _("Cards"), Icon: LayoutGridIcon },
    { view: "large", label: () => _("Large cards"), Icon: RectangleHorizontalIcon },
]

const GRID_CLASSES: Record<Exclude<PickerView, "list">, string> = { cards: "grid grid-cols-3 gap-3", large: "grid grid-cols-2 gap-3" }

/** The one attach dialog for the whole app: search, sources, upload action, recent system files. */
export const AttachPickerDialog = (props: AttachPickerDialogProps) => (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
        <DialogContent showCloseButton={false} className="gap-0 overflow-hidden p-0 sm:max-w-[680px]" aria-describedby={undefined}>
            <DialogTitle className="sr-only">{_("Attach")}</DialogTitle>
            {/* Gated on open so search, source and selection start fresh every time. */}
            {props.open && <AttachPicker {...props} />}
        </DialogContent>
    </Dialog>
)

const AttachPicker = ({ onOpenChange, onUploadFiles, onPickSystemFiles, documents = [], onPickDocument }: AttachPickerDialogProps) => {
    const [search, setSearch] = useState("")
    const [source, setSource] = useState<PickerSource>("all")
    const [activeIndex, setActiveIndex] = useState(0)
    const [checked, setChecked] = useState<Record<string, SystemFile>>({})
    const [view, setView] = useAttachPickerView()
    const fileInput = useRef<HTMLInputElement>(null)
    const { files, isLoading } = useAttachableFiles(search, source !== "upload" && source !== "documents")

    const sources = sourcesFor(Boolean(onPickDocument))
    const items = buildItems(source, files, documents, search)
    const checkedFiles = Object.values(checked)
    const close = () => onOpenChange(false)

    const changeSource = (next: PickerSource) => { setSource(next); setActiveIndex(0) }

    const toggleFile = (file: SystemFile) =>
        setChecked(({ [file.file_url]: existing, ...rest }) => (existing ? rest : { ...rest, [file.file_url]: file }))

    const activate = (item: PickerItem) => {
        if (item.kind === "upload") return fileInput.current?.click()
        if (item.kind === "file") return toggleFile(item.file)
        onPickDocument?.(item.document)
        close()
    }

    const attachChecked = () => { onPickSystemFiles(checkedFiles); close() }

    const onKeyDown = (event: KeyboardEvent) => {
        const step = { ArrowDown: 1, ArrowUp: -1 }[event.key] as 1 | -1 | undefined
        if (step) {
            event.preventDefault()
            setActiveIndex((index) => stepIndex(index, step, COLUMNS[view], items.length))
        } else if (event.key === "Enter" && items[activeIndex]) {
            event.preventDefault()
            if ((event.metaKey || event.ctrlKey) && checkedFiles.length) attachChecked()
            else activate(items[activeIndex])
        } else if ((event.key === "ArrowLeft" || event.key === "ArrowRight") && !search) {
            event.preventDefault()
            changeSource(stepSource(sources, source, event.key === "ArrowRight" ? 1 : -1))
        }
    }

    return (
        <div onKeyDown={onKeyDown} className="flex min-h-0 flex-col">
            <input ref={fileInput} type="file" multiple hidden onChange={(event) => {
                const picked = Array.from(event.target.files ?? [])
                event.target.value = ""
                if (picked.length) { onUploadFiles(picked); close() }
            }} />
            <div className="flex items-center gap-3 px-5 pt-4">
                <SearchIcon className="size-4 shrink-0 text-ink-gray-5" />
                <input
                    autoFocus
                    value={search}
                    onChange={(event) => { setSearch(event.target.value); setActiveIndex(0) }}
                    placeholder={_("Search files")}
                    aria-label={_("Search files")}
                    className="min-w-0 flex-1 bg-transparent text-p-lg text-ink-gray-8 outline-none placeholder:text-ink-gray-4"
                />
            </div>
            <div className="flex items-center border-b px-4 py-3">
            <div role="tablist" className="flex gap-1">
                {sources.map((name) => (
                    <button key={name} type="button" role="tab" aria-selected={name === source} onClick={() => changeSource(name)}
                        className={cn("rounded-md px-3 py-1.5 text-sm text-ink-gray-7 hover:bg-surface-gray-2", name === source && "bg-surface-gray-3 text-ink-gray-9")}>
                        {SOURCE_LABELS[name]()}
                    </button>
                ))}
            </div>
            <div role="group" aria-label={_("View")} className="ms-auto flex gap-0.5">
                {VIEW_OPTIONS.map(({ view: option, label, Icon }) => (
                    <Button key={option} type="button" variant="ghost" size="sm" isIconButton aria-label={label()} title={label()} aria-pressed={option === view}
                        className={cn(option === view && "bg-surface-gray-3 text-ink-gray-9")} onClick={() => setView(option)}>
                        <Icon />
                    </Button>
                ))}
            </div>
            </div>
            <div role="listbox" className={cn("h-80 overflow-y-auto px-3 py-2", view !== "list" && `${GRID_CLASSES[view]} content-start auto-rows-max`)}>
                {items.map((item, index) => {
                    const rowProps = { item, isActive: index === activeIndex, isChecked: item.kind === "file" && item.file.file_url in checked, onActivate: () => activate(item), onHover: () => setActiveIndex(index) }
                    return view === "list" ? <AttachPickerRow key={item.id} {...rowProps} /> : <AttachPickerCard key={item.id} view={view} {...rowProps} />
                })}
                {isLoading && <Skeleton className="m-3 h-4 w-1/2" />}
                {!isLoading && items.every((item) => item.kind === "upload") && source !== "upload" && (
                    <p className="col-span-full p-6 text-center text-p-sm text-ink-gray-5">{_("No files found")}</p>
                )}
            </div>
            <div className="flex items-center gap-5 border-t px-5 py-3 text-xs text-ink-gray-6">
                <Hint label={_("Navigate")} keys={[<ArrowUpIcon key="u" />, <ArrowDownIcon key="d" />]} />
                <Hint label={_("Select")} keys={[<CornerDownLeftIcon key="e" />]} />
                <Hint label={_("Change source")} keys={[<ArrowLeftIcon key="l" />, <ArrowRightIcon key="r" />]} />
                {checkedFiles.length > 0 && (
                    <Button size="sm" className="ms-auto" onClick={attachChecked}>{_("Attach {0}", [String(checkedFiles.length)])}</Button>
                )}
            </div>
        </div>
    )
}

const Hint = ({ label, keys }: { label: string; keys: React.ReactNode[] }) => (
    <span className="flex items-center gap-2">{label}<span className="flex gap-1">{keys.map((key, index) => <Kbd key={index}>{key}</Kbd>)}</span></span>
)
