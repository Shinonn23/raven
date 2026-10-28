import { useState } from "react"
import { PaperclipIcon } from "lucide-react"
import { Button } from "@components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@components/ui/tooltip"
import _ from "@lib/translate"
import { AttachPickerDialog, type AttachPickerDialogProps } from "./AttachPickerDialog"

/** The "Attach file" paperclip — every composer in the app uses this, so they all open the same dialog. */
export const AttachFileButton = (props: Omit<AttachPickerDialogProps, "open" | "onOpenChange">) => {
    const [open, setOpen] = useState(false)
    return (
        <>
            <Tooltip>
                <TooltipTrigger asChild>
                    <Button type="button" variant="ghost" size="sm" isIconButton aria-label={_("Attach file")} onClick={() => setOpen(true)}>
                        <PaperclipIcon />
                    </Button>
                </TooltipTrigger>
                <TooltipContent>{_("Attach file")}</TooltipContent>
            </Tooltip>
            <AttachPickerDialog {...props} open={open} onOpenChange={setOpen} />
        </>
    )
}
