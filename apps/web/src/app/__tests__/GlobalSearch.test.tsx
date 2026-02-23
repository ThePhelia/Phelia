import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GlobalSearch from "@/app/components/GlobalSearch";
import type { MetaSearchItem } from "@/app/types/meta";
import { renderWithProviders } from "@/app/test-utils";

const navigateMock = vi.fn();
const useMetaSearchMock = vi.fn();

const results: MetaSearchItem[] = [
  {
    id: "m1",
    type: "movie",
    provider: "tmdb",
    title: "The Matrix",
    year: 1999,
    poster: "https://example.com/matrix.jpg",
    subtitle: "1999",
  },
  {
    id: "a2",
    type: "album",
    provider: "discogs",
    title: "Discovery",
    year: 2001,
    poster: "https://example.com/discovery.jpg",
    subtitle: "Daft Punk",
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
  useMetaSearch: (query: string) => useMetaSearchMock(query),
}));

describe("GlobalSearch", () => {
  beforeEach(() => {
    localStorage.clear();
    navigateMock.mockReset();
    useMetaSearchMock.mockImplementation((q: string) => {
      if (!q || q.length <= 1) {
        return { data: undefined, isFetching: false };
      }
      return {
        data: { items: results },
        isFetching: false,
      };
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("uses filtered keyboard navigation and opens highlighted item on enter", async () => {
    vi.useFakeTimers();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    renderWithProviders(<GlobalSearch />);

    const input = screen.getByPlaceholderText(/search/i);
    await user.click(input);
    await user.type(input, "Matrix");

    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    expect(screen.getByText("The Matrix")).toBeInTheDocument();

    await user.click(screen.getAllByText(/^movie$/i)[0]);
    await user.click(input);
    await user.keyboard("{ArrowDown}{ArrowDown}{Enter}");

    expect(navigateMock).toHaveBeenCalledWith("/details/movie/m1?provider=tmdb", {
      state: { backgroundLocation: { pathname: "/", key: "test" } },
    });

    const stored = localStorage.getItem("phelia:recent-searches");
    expect(stored && JSON.parse(stored)).toContain("Matrix");
  });

  it("clamps highlight and gracefully no-ops enter when filtered list becomes empty", async () => {
    vi.useFakeTimers();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    renderWithProviders(<GlobalSearch />);

    const input = screen.getByPlaceholderText(/search/i);
    await user.click(input);
    await user.type(input, "Matrix");

    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    await user.keyboard("{ArrowDown}");
    await user.click(screen.getByText(/^tv$/i));

    expect(screen.getByText(/no results found/i)).toBeInTheDocument();

    await user.click(input);
    await user.keyboard("{Enter}");
    expect(navigateMock).not.toHaveBeenCalled();

  });

  it("shows recent searches when available", async () => {
    localStorage.setItem("phelia:recent-searches", JSON.stringify(["Alien"]));
    useMetaSearchMock.mockImplementation(() => ({ data: undefined, isFetching: false }));

    const user = userEvent.setup();
    renderWithProviders(<GlobalSearch />);

    const input = screen.getByPlaceholderText(/search/i);
    await user.click(input);

    expect(await screen.findByText(/recent/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Alien" })).toBeInTheDocument();
  });
});
