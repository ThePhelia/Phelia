import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TorrentSearchDialog from "@/app/components/TorrentSearchDialog";
import type { SearchResultItem } from "@/app/lib/types";
import { renderWithProviders } from "@/app/test-utils";

const { mutateAsync, resetMock, setOpenMock } = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  resetMock: vi.fn(),
  setOpenMock: vi.fn(),
}));

const mockResult: SearchResultItem = {
  id: "example",
  kind: "movie",
  title: "Example Torrent",
  meta: {
    confidence: 0.87,
    jackett: {
      magnet: "magnet:?xt=urn:btih:example",
      url: "https://example.com/torrent",
      size: "1 GB",
      indexer: "Indexer",
      category: "Movies",
      seeders: 12,
      leechers: 3,
      tracker: "ExampleTracker",
    },
    providers: [],
    reasons: [],
    needs_confirmation: false,
    source_kind: "movie",
  },
};

const mockTorrentState = {
  open: true,
  setOpen: setOpenMock,
  isLoading: false,
  results: [mockResult],
  message: undefined as string | undefined,
  jackettUiUrl: undefined as string | undefined,
  error: undefined as string | undefined,
  metaError: undefined as string | undefined,
  activeItem: { title: "Example Torrent" },
  query: "Example Torrent",
};

vi.mock("@/app/stores/torrent-search", () => ({
  useTorrentSearch: (selector?: (state: typeof mockTorrentState) => unknown) =>
    selector ? selector(mockTorrentState) : mockTorrentState,
}));

vi.mock("@/app/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/app/lib/api")>("@/app/lib/api");
  return {
    ...actual,
    useCreateDownload: () => ({
      mutateAsync,
      isPending: false,
      error: null,
      reset: resetMock,
    }),
  };
});

describe("TorrentSearchDialog", () => {
  beforeEach(() => {
    mutateAsync.mockReset().mockResolvedValue({ id: 1 });
    resetMock.mockReset();
    setOpenMock.mockReset();
    mockTorrentState.results = [mockResult];
    mockTorrentState.error = undefined;
    mockTorrentState.metaError = undefined;
    mockTorrentState.message = undefined;
    mockTorrentState.open = true;
  });

  it("invokes the create download mutation when add download clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TorrentSearchDialog />);

    await user.click(screen.getByRole("button", { name: /add download/i }));

    await waitFor(() => {
      expect(resetMock).toHaveBeenCalled();
      expect(mutateAsync).toHaveBeenCalledWith({ magnet: "magnet:?xt=urn:btih:example" });
    });
  });
});
