export const extractUrls = (text: string): string[] => {
  const matches = text.match(/https?:\/\/[^\s]+/g) ?? [];
  return matches.map((url) => url.trim()).filter((url, index, list) => list.indexOf(url) === index);
};
