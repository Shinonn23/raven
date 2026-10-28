/** The files on the clipboard, e.g. a screenshot. Text wins when both are there (copying cells from a sheet also puts a picture on the clipboard). */
export const pastedFiles = (clipboard: Pick<DataTransfer, "files" | "getData"> | null, now = new Date()): File[] => {
    if (!clipboard || clipboard.getData("text/plain")) return []
    return Array.from(clipboard.files).map((file, index) => nameIfGeneric(file, now, index))
}

/** A pasted screenshot is always called "image.png"; give each its own name so they can be told apart. */
const nameIfGeneric = (file: File, now: Date, index: number): File => {
    if (!/^image\.\w+$/i.test(file.name)) return file
    const extension = file.name.split(".").pop()
    const stamp = now.toISOString().replace(/[-:T]/g, "").slice(0, 14)
    return new File([file], `pasted-image-${stamp}${index ? `-${index + 1}` : ""}.${extension}`, { type: file.type })
}
