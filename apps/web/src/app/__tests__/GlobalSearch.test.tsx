import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GlobalSearch from "@/app/components/GlobalSearch";
import type { DiscoverItem, SearchParams } from "@/app/lib/types";
import { renderWithProviders } from "@/app/test-utils";

const navigateMock = vi.fn();
const fetchNextPage = vi.fn();
const useSearchMock = vi.fn();

const results: DiscoverItem[] = [
  {
    id: "m1",
    kind: "movie",
    title: "The Matrix",
    year: 1999,
    genres: ["Sci-Fi"],
    poster: "https://example.com/matrix.jpg",
  },
  {
    id: "a2",
    kind: "album",
    title: "Discovery",
    year: 2001,
    genres: ["Electronic"],
    poster: "https://example.com/discovery.jpg",
  },
];

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
    useLocation: () => ({ pathname: "/", key: "test" }),
  };
});

vi.mock("@/app/lib/api", () => ({
  useSearch: (params: SearchParams) => useSearchMock(params),
}));

describe("GlobalSearch", () => {
  beforeEach(() => {
    localStorage.clear();
    navigateMock.mockReset();
    fetchNextPage.mockReset();
    useSearchMock.mockImplementation(({ q }) => {
      if (!q || q.length <= 1) {
        return { data: undefined, fetchNextPage, hasNextPage: false, isFetching: false };
      }
      return {
        data: { pages: [{ items: results }] },
        fetchNextPage,
        hasNextPage: false,
        isFetching: false,
      };
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("allows keyboard navigation across results", async () => {
    vi.useFakeTimers();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    renderWithProviders(<GlobalSearch />);

    const input = screen.getByPlaceholderText(/search/i);
    await user.click(input);
    await user.type(input, "Matrix");

    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    await screen.findByText("The Matrix");

    await user.keyboard("{ArrowDown}{Enter}");

    expect(navigateMock).toHaveBeenCalledWith("/details/music/a2", {
      state: { backgroundLocation: { pathname: "/", key: "test" } },
    });

    const stored = localStorage.getItem("phelia:recent-searches");
    expect(stored && JSON.parse(stored)).toContain("Matrix");
  });

  it("shows recent searches when available", async () => {
    localStorage.setItem("phelia:recent-searches", JSON.stringify(["Alien"]));
    useSearchMock.mockImplementation(({ q }) => ({
      data: undefined,
      fetchNextPage,
      hasNextPage: false,
      isFetching: false,
    }));

    const user = userEvent.setup();
    renderWithProviders(<GlobalSearch />);

    const input = screen.getByPlaceholderText(/search/i);
    await user.click(input);

    expect(await screen.findByText(/recent/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Alien" })).toBeInTheDocument();
  });
});
