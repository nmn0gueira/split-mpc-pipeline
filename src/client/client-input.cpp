#include "Math/gfp.h"
#include "Math/gf2n.h"
#include "Networking/sockets.h"
#include "Networking/ssl_sockets.h"
#include "Tools/int.h"
#include "Math/Setup.h"
#include "Protocols/fake-stuff.h"

#include "Math/gfp.hpp"
#include "Client.hpp"

#include <sodium.h>
#include <iostream>
#include <sstream>
#include <fstream>


enum class NumType { Int, Float, Invalid };

NumType detect_number(const std::string& string)
{
    std::istringstream iss(string);
    std::string token;
    if (!(iss >> token))
        return NumType::Invalid;

    size_t start = (!token.empty() && token[0] == '-') ? 1 : 0;
    bool is_int = start < token.size();
    for (size_t i = start; i < token.size() && is_int; i++)
        is_int = std::isdigit((unsigned char)token[i]);
    if (is_int)
        return NumType::Int;

    char* endPtr = nullptr;
    std::strtod(token.c_str(), &endPtr);
    if (endPtr != nullptr && *endPtr == '\0')
        return NumType::Float;

    return NumType::Invalid;
}


template<class T>
std::vector<T> wrap_values(const std::vector<string> &strs) {
    if (strs.empty())
        throw runtime_error("Empty vector");

    std::vector<T> values;
    values.reserve(strs.size());
    
    const std::string& first = strs.front();
    NumType num_type = detect_number(first);

    if (num_type == NumType::Int) {
        for (const auto& s : strs) {
            values.emplace_back(!s.empty() && s[0] == '-' ? std::stol(s) : (long)std::stoul(s));
        }
        return values;
    }
    
    if (num_type == NumType::Float) {
        for (const auto& s : strs) {
            values.emplace_back(long(round(std::stod(s) * exp2(16))));    // sfix with f = 16
        }
        return values;
    }

    throw runtime_error("Vector contains invalid elements");
}


// stoul fails for Z2<128> outputs (39-digit strings exceed ULONG_MAX) so we do this digit accumulation mod 2^64 to take the low 64 bits of the ring size
template<class U>
long long to_signed(const U& val) {
    std::ostringstream oss;
    oss << val;
    unsigned long long u = 0;
    for (char c : oss.str())
        if (c >= '0' && c <= '9') u = u * 10 + (c - '0');
    return (long long)u;
}


template<class T, class U>
void run(const std::vector<std::vector<string>> &data, Client& client)
{
    for (const auto& row : data) {
        client.send_private_inputs<T>(wrap_values<T>(row));
    }

    cout << "Sent all private inputs to each SPDZ engine, waiting for result..." << endl;

    int batch_id = 0;
    while(true) {
        std::vector<U> header = client.receive_outputs<T>(2);
        long long output_length = to_signed(header[0]);
        long long type_id = to_signed(header[1]);

        if (output_length == -1 && type_id == -1) // Termination header
            return;

        std::vector<U> result = client.receive_outputs<T>(output_length);
        cout << "Batch " << batch_id << ":" << endl;

        if (type_id == 0) { // sint
            for (const auto& r : result) {
                cout << "Output: " << to_signed(r) << endl;
            }
        }

        else if (type_id == 1) { // sfix
            for (const auto& r : result) {
                cout << "Output: " << (double)to_signed(r) / exp2(16) << endl;
            }
        }

        else
            throw std::runtime_error("Unrecognized type id: " + std::to_string(type_id));

        ++batch_id;
    }
}


std::vector<std::vector<std::string>> read_data(const std::string& filename)
{
    std::ifstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }

    std::vector<std::vector<std::string>> rows;
    std::string line;
    while (std::getline(file, line)) {
        std::stringstream ss(line);
        std::string cell;
        rows.emplace_back();
        auto& row = rows.back();

        while (std::getline(ss, cell, ' ')) {
            row.emplace_back(std::move(cell));
        }
    }

    return rows;
}


int main(int argc, char** argv)
{
    int client_id;
    int nparties;
    std::string input_file;
    size_t finish;
    int port_base;
    std::vector<std::string> hostnames;

    auto usage = [&]() -> int {
        std::cerr << "Usage: " << argv[0] << "\n"
                << "  --client_id <client_identifier>          Identifier of this client\n"
                << "  --nparties <number_of_parties>           Number of SPDZ engines (i.e., computing parties) in the computation\n"
                << "  --in <input_file>                        Path to input file (default is Player-Data/Input-P{client_id}-0)\n"
                << "  [--finish]                               Whether to tell SPDZ engines to stop listening for connections\n"
                << "  [--port_base <port>]                     Port base for SPDZ engine's connections (default 14000)\n"
                << "  [--hosts <host_1,host_2,...,host_n>]     Hostnames for the SPDZ engines (default localhost * nparties)\n"
                << std::endl;
        return 1;
    };

    // Very simple arg parser
    std::unordered_map<std::string, std::string> args;
    for (int i = 1; i < argc; ++i) {
        std::string key = argv[i];

        if (key.rfind("--", 0) != 0) {
            std::cerr << "Unexpected positional argument: " << key << '\n';
            return usage();
        }

        bool has_next = (i + 1 < argc);
        bool next_is_flag = has_next && std::string(argv[i + 1]).rfind("-", 0) == 0;

        if (!has_next || next_is_flag) {    // store true
            args[key] = "1";
        } else {
            args[key] = argv[i + 1];
            ++i;
        }
    }

    try {
        client_id   = std::stoi(args.at("--client_id"));
        nparties    = std::stoi(args.at("--nparties"));
        input_file = args.count("--in") ? args.at("--in") : "Player-Data/Input-P" + std::to_string(client_id) + "-0";
        finish = args.count("--finish") ? std::stoi(args.at("--finish")) : 0;
        port_base = args.count("--port_base") ? std::stoi(args.at("--port_base")) : 14000;

        if (args.count("--hosts")) {
            std::istringstream ss(args.at("--hosts"));
            std::string host;
            while (std::getline(ss, host, ',')) {
                hostnames.push_back(host);
            }
        } else {
            hostnames.assign(nparties, "localhost");
        }

        std::cout << "client_id: " << client_id << "\n"
                  << "nparties: " << nparties << "\n"
                  << "input: " << input_file << "\n"
                  << "finish: " << finish << "\n"
                  << "port_base: " << port_base << "\n"
                  << "hosts: ";
        for (const auto& h : hostnames) std::cout << h << ' ';
        std::cout << '\n';
    } catch (const std::out_of_range&) {
        std::cerr << "Missing required argument.\n";
        return usage();
    } catch (const std::invalid_argument&) {
        std::cerr << "Invalid numeric value.\n";
        return usage();
    }


    std::vector<std::vector<std::string>> strs = read_data(input_file);
    
    bigint::init_thread();

    // Setup connections from this client to each party socket
    Client client(hostnames, port_base, client_id);
    auto& specification = client.specification;
    auto& sockets = client.sockets;
    for (int i = 0; i < nparties; i++)
    {
        octetStream os;
        os.store(finish);
        os.Send(sockets[i]);
    }
    cout << "Finish setup socket connections to SPDZ engines." << endl;

    int type = specification.get<int>();
    switch (type)
    {
    case 'p':
    {
        gfp::init_field(specification.get<bigint>());
        cerr << "using prime " << gfp::pr() << endl;
        run<gfp, gfp>(strs, client);
        break;
    }
    case 'R':
    {
        int R = specification.get<int>();
        int R2 = specification.get<int>();
        if (R != R2)
        {
            cerr << "R (" << R << ") different than R2 (" << R2 << ")." << endl;
        }

        switch (R)
        {
        case 64:
            run<Z2<64>, Z2<64>>(strs, client);
            break;
        case 128:
            //run<Z2<128>, Z2<64>>(strs, client);   // This was the original, but it resulted in errors when assigning the output of client.receive_outputs to a vector<U>, apparently due to conversion errors from Z2<128> to Z2<64>
            run<Z2<128>, Z2<128>>(strs, client);
            break;
        default:
            cerr << R << "-bit ring not implemented";
            exit(1);
        }
        break;
    }
    default:
        cerr << "Type " << type << " not implemented";
        exit(1);
    }

    return 0;
}
